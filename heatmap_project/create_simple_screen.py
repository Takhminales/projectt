from PIL import Image

def create_simple_screen():
    """
    Создаёт белое изображение 400×200 и сохраняет его под именем simple_screen.png.
    Если файл уже существует, будет перезаписан.
    """
    img = Image.new("RGB", (400, 200), color=(255, 255, 255))
    img.save("simple_screen.png")
    print("Файл 'simple_screen.png' создан (или перезаписан).")

if __name__ == "__main__":
    create_simple_screen()
