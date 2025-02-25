from PIL import Image, ImageDraw

# Создаем новое изображение (например, 500x500 пикселей)
image = Image.new('RGB', (500, 500), color='white')

# Сохраняем изображение
image.save('test_image.png')
