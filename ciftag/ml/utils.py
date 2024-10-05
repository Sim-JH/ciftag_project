from PIL import Image


def resize_with_padding(img, target_size=(224, 224)):
    # 이미지의 비율을 유지하면서 리사이즈하고 패딩 추가
    img.thumbnail(target_size, Image.Resampling.LANCZOS)  # 비율을 유지하며 리사이즈

    # 배경을 흰색으로 패딩 추가하여 224x224로 맞춤
    new_img = Image.new("RGB", target_size, (255, 255, 255))  # 흰색 배경
    new_img.paste(
        img,
        ((target_size[0] - img.size[0]) // 2, (target_size[1] - img.size[1]) // 2)
    )
    return new_img