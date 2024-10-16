from typing import Union

import cv2
import numpy as np
from mtcnn import MTCNN


class FaceCropper:
    """얼굴 중앙 탐지 후 정사각형으로 crop"""
    def __init__(self):
        # MTCNN 모델 초기화
        self.detector = MTCNN()

    def detect_and_crop(self, image_path) -> Union[np.ndarray, None]:
        # 이미지 불러오기
        image = cv2.imread(image_path)

        if image is None:
            raise ValueError("Image not found or unable to load.")

        # 얼굴 탐지
        results = self.detector.detect_faces(image)

        if len(results) == 0:
            return None

        # 첫 번째 얼굴만 사용
        face = results[0]
        x, y, w, h = face['box']

        # 얼굴 중앙 계산
        face_center_x = x + w // 2
        face_center_y = y + h // 2

        # 원본 이미지의 크기
        height, width, _ = image.shape

        # 정사각형으로 자를 수 있는 최대 크기 계산
        square_size = min(width, height)

        # 자를 영역의 좌표 계산 (얼굴이 중앙에 오도록)
        half_square = square_size // 2
        x_start = max(0, face_center_x - half_square)
        y_start = max(0, face_center_y - half_square)
        x_end = min(width, x_start + square_size)
        y_end = min(height, y_start + square_size)

        # 이미지 자르기 (정사각형)
        cropped_image = image[y_start:y_end, x_start:x_end]
        return cropped_image

    @staticmethod
    def resize_image(image: np.ndarray, output_size: int) -> np.ndarray:
        # 원하는 사이즈로 리사이즈
        resized_image = cv2.resize(image, (output_size, output_size))
        return resized_image
