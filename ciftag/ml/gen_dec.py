import torch

from typing import List, Tuple, Union
from io import BytesIO

from PIL import Image
from transformers import (
    BlipProcessor,
    BlipForConditionalGeneration,
    CLIPProcessor,
    CLIPModel,
    GPT2Tokenizer,
    GPT2LMHeadModel,
    pipeline
)

import ciftag.utils.logger as logger

logs = logger.Logger('ML')


class ImageDescriber:
    def __init__(self, model_type: str = 'BLIP', translate=False):
        """ 이미지 기반 설명 생성
        model_type: 사용할 모델 종류 (현재 BLIP만 사용)
        """
        self.model_type = model_type
        self.translate = translate

        # 선택한 모델 초기화
        self.model, self.processor = self.initialize_model()

        # TODO 아래 후처리 LLM은 허깅페이스 무료 모델을 쓰지만 GPT API로 GPT4 쓰는게 더 훨씬 나을듯
        # 번역 파이프라인 초기화
        # 버전문제로 tf 대신 pytorch 사용
        # (영어 -> 한글 번역) !성능 이슈
        self.translator_ko = pipeline(
            "translation_en_to_ko", model="NHNDQ/nllb-finetuned-en2ko", framework="pt"
        )
        # (한글 -> 영어 번역)
        self.translator_en = pipeline(
            "translation_ko_to_en", model="NHNDQ/nllb-finetuned-ko2en", framework="pt"
        )

        # GPT 모델 초기화 !성능 이슈
        self.gpt_model = GPT2LMHeadModel.from_pretrained('gpt2')
        self.gpt_tokenizer = GPT2Tokenizer.from_pretrained('gpt2')
        self.gpt_model.eval()

    def initialize_model(self):
        if self.model_type == 'BLIP':
            model = BlipForConditionalGeneration.from_pretrained('Salesforce/blip-image-captioning-base')
            processor = BlipProcessor.from_pretrained('Salesforce/blip-image-captioning-base')
        else:
            raise ValueError(f"지원하지 않는 모델 타입: {self.model_type}")

        return model, processor

    def load_image(self, mode: str, img_source: Union[bytes, str]) -> Image.Image:
        """
        mode에 따라 이미지 바이트 데이터 또는 로컬 경로에서 이미지를 불러오는 함수
        """
        if mode == 'byte':
            img = Image.open(BytesIO(img_source)).convert("RGB")
        else:
            img = Image.open(img_source).convert("RGB")
        return img

    def generate_descriptions(
            self,
            image_source: List[Tuple[str, Union[bytes, str], str]],
            mode: str
    ) -> List[Tuple[str, str]]:
        """
        BLIP 또는 CLIP 모델을 사용해 이미지에 대해 설명을 생성하는 함수
        """
        results = []

        for data_idx, img_source, tags in image_source:
            # 이미지 로드
            img = self.load_image(mode, img_source)

            if self.model_type == 'BLIP':
                # BLIP 모델을 사용하는 경우
                inputs = self.processor(images=img, return_tensors="pt")

                # 설명 생성
                with torch.no_grad():
                    out = self.model.generate(**inputs)

                description = self.processor.decode(out[0], skip_special_tokens=True)

                # GPT로 태그를 반영하여 설명을 수정 (테스트 결과 GPT2 성능이 영 좋지 못해 일단 보류)
                # if len(tags):
                #     tag_prompt = self.translate_text(tags, 'en')
                #     prompt = (
                #         f"This image was crawled using the tags: '{tag_prompt}'. "
                #         f"The BLIP model generated the following description: '{description}'. "
                #         f"Please refine the description to emphasize the key elements related to the tags: {tag_prompt}."
                #     )
                #
                #     gpt_input = self.gpt_tokenizer.encode(prompt, return_tensors="pt")
                #
                #     with torch.no_grad():
                #         outputs = self.gpt_model.generate(gpt_input, max_new_tokens=50, num_return_sequences=1)
                #
                #     description = self.gpt_tokenizer.decode(outputs[0], skip_special_tokens=True)

            # 영어 설명을 한글로 번역
            if self.translate:
                description = self.translate_text(description, 'ko')
                logs.log_data(f'translate: {description}')

            results.append((data_idx, description))

        return results

    def translate_text(self, text: str, ltype='en') -> str:
        """영어 설명을 한글로 번환"""
        if ltype == "en":
            translated = self.translator_en(text, max_length=512)
        else:
            translated = self.translator_ko(text, max_length=1024)

        #  첫 번째 번역 결과만 사용
        translated_text = translated[0]['translation_text'].strip()  # 첫 번째 번역 결과만 사용

        # 언어 코드 붙어서 나올 시 제거
        if translated_text[:2].isalpha():  # 시작하는 첫 두 글자가 알파벳이면 제거
            translated_text = translated_text[2:].strip()

        return translated_text

    def process_image(
            self,
            image_source: List[Tuple[str, Union[bytes, str], str]],
            mode: str
    ) -> List[Tuple[str, str]]:
        """ 이미지 설명 생성
        image_source: 리스트 [(데이터 인덱스, 이미지 소스, 태그 목록 (CLIP 사용 시))]
        mode: image_sources 제공 형식 byte/path
        """
        if mode not in ['byte', 'path']:
            raise ValueError("mode는 'byte' 또는 'path' 중 택일")

        # 이미지 설명 생성
        results = self.generate_descriptions(image_source, mode)

        # 결과 반환
        return results


