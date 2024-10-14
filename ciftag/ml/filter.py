import os
import tempfile
import zipfile
from typing import Optional, Tuple, List, Union, Literal
from io import BytesIO

import numpy as np
from PIL import Image

import torch
from tensorflow.keras.applications import ResNet50
from tensorflow.keras.applications.resnet50 import preprocess_input as resnet_preprocess
from tensorflow.keras.preprocessing import image

import timm
from facenet_pytorch import InceptionResnetV1

from torchvision import transforms
from sklearn.metrics.pairwise import cosine_similarity

import ciftag.utils.logger as logger
from ciftag.ml.utils import resize_with_padding

logs = logger.Logger('ML')


class ImageFilter:
    def __init__(
            self,
            sample_image_path: Optional[str] = None,
            threshold: float = 0.8,
            model_type: str = "ResNet50"
    ):
        """
        sample_image_path: 샘플 이미지 zip 파일 경로
        target_tags: 타겟 이미지 태그
        threshold: threshold
        """
        self.threshold = threshold
        self.model_type = model_type

        # 선택한 모델 초기화
        self.model, self.preprocess_input = self.initialize_model()

        # 샘플 이미지 임베딩 추출
        self.sample_embeddings = self.extract_and_embed_sample_images(sample_image_path)

    def initialize_model(self):
        """모델 타입에 따라 다른 모델 및 전처리 함수 반환"""
        if self.model_type == "ResNet50":
            model = ResNet50(weights='imagenet', include_top=True)
            preprocess_input = resnet_preprocess
        elif self.model_type == "FaceNet":
            # FaceNet 초기화 (외부 라이브러리 필요)
            model = InceptionResnetV1(pretrained='vggface2').eval()  # FaceNet 모델
            preprocess_input = lambda x: x  # FaceNet은 별도 전처리 불필요
        elif self.model_type == "SwinTransformer":
            # Swin Transformer 초기화
            model = timm.create_model('swin_base_patch4_window7_224', pretrained=True)
            model.eval()  # Swin Transformer는 eval 모드로 설정
            preprocess_input = transforms.Compose([
                transforms.Resize((224, 224)),  # 모델에 맞는 크기로 리사이즈
                transforms.ToTensor(),  # 이미지를 Tensor로 변환
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],  # Swin Transformer에서 권장하는 평균
                    std=[0.229, 0.224, 0.225]    # Swin Transformer에서 권장하는 표준편차
                ),
            ])
        else:
            raise ValueError(f"지원하지 않는 모델 타입: {self.model_type}")

        return model, preprocess_input

    def extract_and_embed_sample_images(self, zip_file_path: str) -> np.ndarray:
        """Zip 파일에서 이미지 추출 및 임베딩 계산"""
        sample_embeddings = []

        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            with tempfile.TemporaryDirectory() as tmpdirname:
                zip_ref.extractall(tmpdirname)
                image_files = [os.path.join(tmpdirname, f) for f in os.listdir(tmpdirname)]

                for img_file in image_files:
                    if img_file.lower().endswith(('.png', '.jpg', '.jpeg')):
                        embedding = self.get_image_embedding('path', img_file)
                        sample_embeddings.append(embedding)

        return np.array(sample_embeddings)

    def load_image(self, mode, img_source) -> Image.Image:
        """mode에 따라 이미지 URL 또는 로컬 경로에서 타겟 이미지를 불러오기"""
        if mode == 'byte':
            img = Image.open(BytesIO(img_source))
        else:
            img = Image.open(img_source)
        return img

    def get_image_embedding(self, mode, img_source) -> np.ndarray:
        """이미지에서 임베딩 추출"""
        img = self.load_image(mode, img_source)
        img = resize_with_padding(
            img,
            target_size=(160, 160) if self.model_type == 'FaceNet' else (224, 224)
        )

        if self.model_type == "SwinTransformer" or self.model_type == "FaceNet":
            # PyTorch 기반 모델 - 이미지 텐서로 변환 후 처리
            img_tensor = self.preprocess_input(img)  # PIL 이미지를 Tensor로 변환
            if isinstance(img_tensor, Image.Image):
                img_tensor = transforms.ToTensor()(img_tensor)  # PIL 이미지를 PyTorch 텐서로 변환

            with torch.no_grad():
                img_tensor = img_tensor.unsqueeze(0)  # 배치 차원 추가
                img_embedding = self.model(img_tensor).cpu().numpy().flatten()
        else:
            # Keras 기반 모델 - PIL 이미지를 numpy 배열로 변환 후 처리
            img_array = image.img_to_array(img)
            img_array = np.expand_dims(img_array, axis=0)  # 배치 차원 추가
            img_tensor = self.preprocess_input(img_array)  # 전처리 적용
            img_embedding = self.model.predict(img_tensor).flatten()

        return img_embedding

    def filter_by_similarity(self, mode, image_source_with_file_name):
        """샘플 이미지와의 유사도 기반 필터링"""
        if self.sample_embeddings is None:
            raise ValueError("샘플 이미지 설정 필요")

        filtered_images = []

        for file_name, img_source in image_source_with_file_name:
            img_embedding = self.get_image_embedding(mode, img_source)

            # 샘플 이미지와의 유사도 계산
            similarity = cosine_similarity(self.sample_embeddings, img_embedding.reshape(1, -1))

            # 유사도가 threshold 이상인 경우만 필터링
            if np.max(similarity) > self.threshold:
                filtered_images.append((file_name, img_source))

        return filtered_images

    def combined_filtering(
            self,
            mode: str,
            image_source_with_file_name: List[Tuple[str, Union[bytes, str]]]
    ):
        """필수: 태그 기반 필터링 + 선택: 유사도 기반 필터링
        image_source_with_file_name: 리스트 [{파일명: 이미지 소스}]
        mode: image_sources 제공 형식 List[(byte/path)]
        """
        if mode not in ['byte', 'path']:
            raise ValueError("mode는 'byte' 또는 'path' 중 택일")

        logs.log_data(f"{self.model_type} 전달된 이미지 수: {len(image_source_with_file_name)}")
        # 유사도 기반 필터링
        final_filtered_images = self.filter_by_similarity(mode, image_source_with_file_name)
        logs.log_data(f"{self.model_type} {self.threshold} 유사도 기반 필터링을 통과한 이미지 수: {len(final_filtered_images)}")
        return final_filtered_images
