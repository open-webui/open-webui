from pathlib import Path
from PIL import ImageDraw, ImageFilter
from PIL.Image import Image, Resampling
from PIL.Image import new as new_image

# 이미지 크기와 기본 설정
img_size = (500, 500)
rect_size = (50, 200)
gap = (20, 50)
circle_radius = 250
radius_gap: int = 10
corner_radius = 30  # 직사각형의 모서리 반경
num_rects = 5
small_circle_radius = corner_radius  # 작은 원의 반지름


def draw_round_rectangles(draw, positions, rect_size, color, corner_radius):
    for x, y in positions:
        draw.rounded_rectangle(
            [(x, y), (x + rect_size[0], y + rect_size[1])],
            radius=corner_radius,
            fill=color,
        )


def draw_small_circles(draw, positions, color):
    ...
    # circle_y = positions[0][1] + rect_size[1]  # 첫 번째 막대의 y 좌표
    # for x, _ in positions[1:-1]:  # 첫 번째와 마지막 막대를 제외
    #     circle_x = x + rect_size[0] // 2  # 막대의 중앙 x 좌표
    #     draw.ellipse(
    #         [
    #             (circle_x - small_circle_radius, circle_y - small_circle_radius),
    #             (circle_x + small_circle_radius, circle_y + small_circle_radius),
    #         ],
    #         fill=color,
    #     )


def to_coordinate(
    pos: int,
    rect_size: tuple[int, int],
    img_size: tuple[int, int],
    num_rects: int,
    gap: tuple[int, int],
) -> tuple[float, float]:
    x = (img_size[0] - (rect_size[0] * num_rects + gap[0] * (num_rects - 1))) // 2
    return (
        x + (rect_size[0] + gap[0]) * pos,
        img_size[1] / 2
        - rect_size[1] / 2
        + gap[1] * abs(pos - (num_rects - 1) / 2)
        - ((num_rects - 1) / 2 - 1) * gap[1],
    )


def apply_antialiasing(image: Image, downscale_factor: int = 2):
    original_size = image.size
    scaled_size = (
        original_size[0] * downscale_factor,
        original_size[1] * downscale_factor,
    )

    # 이미지 확대 후 다시 축소하여 안티앨리어싱 효과 적용
    image = image.resize(scaled_size, Resampling.LANCZOS)
    image = image.filter(ImageFilter.BLUR)
    image = image.resize(original_size, Resampling.LANCZOS)

    return image


def save_image(image: Image, filename: str) -> str:
    existing_files = list(Path(".").rglob(Path(filename).name))
    if existing_files:
        for file in existing_files:
            image.save(file)
            print(f"- Overwritten: {file}")
    return filename


if __name__ == "__main__":
    positions: list[tuple[float, float]] = [
        to_coordinate(i, rect_size, img_size, num_rects, gap) for i in range(num_rects)
    ]

    ### 1. favicon.png ###
    favicon_img = new_image("RGBA", img_size, (255, 255, 255, 0))
    draw_favicon = ImageDraw.Draw(favicon_img)
    circle_center = (img_size[0] // 2, img_size[1] // 2)
    draw_favicon.ellipse(
        [
            (
                circle_center[0] - (circle_radius - radius_gap),
                circle_center[1] - (circle_radius - radius_gap),
            ),
            (
                circle_center[0] + (circle_radius - radius_gap),
                circle_center[1] + (circle_radius - radius_gap),
            ),
        ],
        fill="white",
    )
    draw_round_rectangles(draw_favicon, positions, rect_size, "black", corner_radius)
    draw_small_circles(draw_favicon, positions, "black")
    favicon_img = apply_antialiasing(favicon_img)
    save_image(favicon_img, "favicon.png")

    ### 2. splash-dark.png ###
    splash_dark_img = new_image("RGBA", img_size, (255, 255, 255, 0))
    draw_splash_dark = ImageDraw.Draw(splash_dark_img)
    draw_round_rectangles(draw_splash_dark, positions, rect_size, "teal", corner_radius)
    draw_small_circles(draw_splash_dark, positions, "teal")
    splash_dark_img = apply_antialiasing(splash_dark_img)
    save_image(splash_dark_img, "splash-dark.png")

    ### 3. splash.png ###
    splash_img = new_image("RGBA", img_size, (255, 255, 255, 0))
    draw_splash = ImageDraw.Draw(splash_img)
    draw_round_rectangles(draw_splash, positions, rect_size, "black", corner_radius)
    draw_small_circles(draw_splash, positions, "black")
    splash_img = apply_antialiasing(splash_img)
    save_image(splash_img, "splash.png")
