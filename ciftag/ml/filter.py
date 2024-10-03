import os
import zipfile
from typing import Optional, Tuple, List, Dict, Union
from io import BytesIO

import requests
import numpy as np
from PIL import Image

from tensorflow.keras.applications import ResNet50
from tensorflow.keras.applications.resnet50 import preprocess_input, decode_predictions
from tensorflow.keras.preprocessing import image
from sklearn.metrics.pairwise import cosine_similarity


class ImageFilter:
    def __init__(
            self,
            sample_image_path: Optional[str] = None,
            target_size: Optional[Union[Tuple[int, int], None]] = None,
            target_tags: Optional[List[str]] = None,
            threshold: float = 0.8,
            mode: str = "path"
    ):
        """
        sample_image_path: 샘플 이미지 zip 파일 경로
        target_size: 타겟 사이즈
        target_tags: 타겟 이미지 태그
        threshold: threshold
        mode: image_sources 제공 형식 List[(byte/path)]
        """
        if sample_image_path is not None and target_size is None:
            raise ValueError("샘플 이미지가 제공되면 target_size는 필수")

        if mode not in ['byte', 'path']:
            raise ValueError("mode는 'byte' 또는 'path' 중 택일")

        self.mode = mode  # URL 또는 로컬 경로 모드
        self.sample_image_path = sample_image_path
        self.target_tags = target_tags
        self.threshold = threshold
        self.target_size = target_size

        # ResNet50 모델 초기화
        self.model = ResNet50(weights='imagenet', include_top=True)  # 분류용 모델
        self.embedding_model = ResNet50(weights='imagenet', include_top=False, pooling='avg')  # 임베딩 추출용 모델

        # 샘플 이미지 제공받을 시, 임베딩 미리 추출
        if self.sample_image_path:
            self.sample_embeddings = self.extract_and_embed_sample_images(self.sample_image_path)
        else:
            self.sample_embeddings = None

    def extract_and_embed_sample_images(self, zip_file_path: str) -> np.ndarray:
        """Zip 파일에서 이미지 추출 및 임베딩 계산"""
        sample_embeddings = []
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall("extracted_samples")  # Zip 파일 추출
            image_files = [os.path.join("extracted_samples", f) for f in os.listdir("extracted_samples")]

            for img_file in image_files:
                if img_file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    embedding = self.get_image_embedding(img_file)
                    sample_embeddings.append(embedding)

        return np.array(sample_embeddings)

    def load_image(self, img_source) -> Image.Image:
        """mode에 따라 이미지 URL 또는 로컬 경로에서 타겟 이미지를 불러오기"""
        if self.mode == 'byte':
            img = Image.open(BytesIO(img_source))
        else:
            img = Image.open(img_source)
        return img

    def get_image_embedding(self, img_source) -> np.ndarray:
        """이미지에서 임베딩 추출"""
        img = self.load_image(img_source)
        img = img.resize(self.target_size)  # target_size로 리사이즈
        img_array = image.img_to_array(img)
        img_array = np.expand_dims(img_array, axis=0)
        img_array = preprocess_input(img_array)

        # 임베딩 벡터 추출
        embedding = self.embedding_model.predict(img_array)
        return embedding

    def classify_image(self, img_source) -> bool:
        """이미지 태그 분류"""
        img = self.load_image(img_source)
        img = img.resize(self.target_size)  # target_size로 리사이즈
        img_array = image.img_to_array(img)
        img_array = np.expand_dims(img_array, axis=0)
        img_array = preprocess_input(img_array)

        # 분류 예측
        preds = self.model.predict(img_array)
        decoded_preds = decode_predictions(preds, top=3)[0]

        # 목표 태그와 일치하는지 확인
        for _, label, score in decoded_preds:
            if label in self.target_tags:
                return True  # 태그가 일치하는 이미지
        return False  # 태그가 일치하지 않는 이미지

    def filter_by_similarity(self, image_source_with_file_name):
        """샘플 이미지와의 유사도 기반 필터링"""
        if self.sample_embeddings is None:
            raise ValueError("샘플 이미지 설정 필요")

        filtered_images = []

        for file_name, img_source in image_source_with_file_name:
            img_embedding = self.get_image_embedding(img_source)

            # 샘플 이미지와의 유사도 계산
            similarity = cosine_similarity(self.sample_embeddings, img_embedding)

            # 유사도가 threshold 이상인 경우만 필터링
            if np.max(similarity) > self.threshold:
                filtered_images.append({file_name: img_source})

        return filtered_images

    def tag_based_filter(self, image_source_with_file_name):
        """태그 기반 필터링"""
        tag_filtered_images = []

        for file_name, img_source in image_source_with_file_name:
            if self.classify_image(img_source):
                tag_filtered_images.append({file_name: img_source})

        return tag_filtered_images

    def combined_filtering(self, image_source_with_file_name: List[Dict[str:Union[bytes, str]]]):
        """필수: 태그 기반 필터링 + 선택: 유사도 기반 필터링
        image_source_with_file_name: {파일명: 이미지 소스 리스트}
        """
        # 1차: 태그 기반 필터링
        tag_filtered_images = self.tag_based_filter(image_source_with_file_name)
        print(f"태그 기반으로 필터링된 이미지 수: {len(tag_filtered_images)}")

        # 2차: 샘플 이미지가 제공된 경우 유사도 기반 필터링
        if self.sample_image_path is not None:
            final_filtered_images = self.filter_by_similarity(tag_filtered_images)
            print(f"유사도 기반으로 필터링된 이미지 수: {len(final_filtered_images)}")
            return final_filtered_images
        else:
            return tag_filtered_images
