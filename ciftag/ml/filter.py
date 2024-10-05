import os
import tempfile
import zipfile
from typing import Optional, Tuple, List, Union
from io import BytesIO

import numpy as np
from PIL import Image

from tensorflow.keras.applications import ResNet50
from tensorflow.keras.applications.resnet50 import preprocess_input, decode_predictions
from tensorflow.keras.preprocessing import image
from sklearn.metrics.pairwise import cosine_similarity

from ciftag.ml.utils import resize_with_padding


class ImageFilter:
    def __init__(
            self,
            sample_image_path: Optional[str] = None,
            threshold: float = 0.8,

    ):
        """
        sample_image_path: 샘플 이미지 zip 파일 경로
        target_tags: 타겟 이미지 태그
        threshold: threshold
        """
        self.threshold = threshold

        # ResNet50 모델 초기화
        self.model = ResNet50(weights='imagenet', include_top=True)   # 임베딩 추출용 모델 (3채널 기반)
        # TODO 흑백 이미지 처리

        # 샘플 이미지 임베딩 추출
        self.sample_embeddings = self.extract_and_embed_sample_images(sample_image_path)

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
        img = resize_with_padding(img)
        img_array = image.img_to_array(img)
        img_array = np.expand_dims(img_array, axis=0)
        img_array = preprocess_input(img_array)

        # 임베딩 벡터 추출 및 flatten
        embedding = self.model.predict(img_array)
        embedding = embedding.flatten()

        return embedding

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

        print(f"전달된 이미지 수: {len(image_source_with_file_name)}")
        # 유사도 기반 필터링
        final_filtered_images = self.filter_by_similarity(mode, image_source_with_file_name)
        print(f"유사도 기반 필터링을 통과한 이미지 수: {len(final_filtered_images)}")
        return final_filtered_images
