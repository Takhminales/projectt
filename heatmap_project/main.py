# Шаг 1. Импорт необходимых модулей
import math
import random
import time

from PIL import Image, ImageDraw


'''
math – для математических функций (exp, pi, cos, sin и т.д.).
random – для генерации случайных чисел (понадобится в случайном блуждании).
time – для замера времени (сравнение производительности).
PIL (Pillow) – для загрузки, создания и сохранения изображений (формат PNG, наложение тепловой карты).

'''

# Шаг 2. Загрузка фонового изображения

def load_background_image(image_path):
    """
    Загружает изображение из файла image_path и переводит его в формат RGBA
    (чтобы можно было накладывать полупрозрачные элементы).
    Возвращает объект PIL.Image и кортеж (width, height).
    """
    image = Image.open(image_path).convert("RGBA")
    return image, image.size


'''
Принимаем путь к изображению image_path, загружаем файл и переводим в RGBA.
Возвращаем сам объект изображения и его размеры (width, height).
'''

# Шаг 3. Генерация данных методом случайного блуждания

def generate_random_walk_data(width, height, num_walkers, points_per_walker, step_size):
    """
    Генерирует набор точек (x, y) с помощью случайного блуждания.
    Параметры:
      width, height       - размеры области (в пикселях);
      num_walkers         - количество "респондентов";
      points_per_walker   - сколько точек генерируется для каждого респондента;
      step_size           - шаг смещения при блуждании.
    Возвращает список кортежей (x, y).
    """
    all_points = []
    for _ in range(num_walkers):
        # Начинаем с случайной позиции внутри [0, width] × [0, height]
        x = random.uniform(0, width)
        y = random.uniform(0, height)
        for _ in range(points_per_walker):
            angle = random.uniform(0, 2 * math.pi)  # случайный угол
            dx = step_size * math.cos(angle)
            dy = step_size * math.sin(angle)
            # Обновляем x, y, следя, чтобы не выйти за границы
            x = max(0, min(width - 1, x + dx))
            y = max(0, min(height - 1, y + dy))
            all_points.append((x, y))
    return all_points

    # Для каждого из num_walkers (агентов) генерируется points_per_walker точек.
    # Координаты перемещаются случайным образом, но не выходят за границы изображения.



# Шаг 4. Собственная реализация гауссовского ядра

def gaussian_kernel(dist_sq, bandwidth):
    """
    Вычисляет вклад точки по гауссовскому ядру при известном расстоянии (в виде dist_sq)
    и параметре сглаживания bandwidth.
    Формула: exp(-dist_sq / (2 * bandwidth^2)) / (2*pi*bandwidth^2).
    """
    return math.exp(-dist_sq / (2 * bandwidth * bandwidth)) / (2 * math.pi * bandwidth * bandwidth)



'''
dist_sq – квадрат расстояния между центром ядра и точкой (dxdx + dydy).
bandwidth – масштаб ядра (определяет «ширину» сглаживания).
'''

# Шаг 5. Метод 1: Brute-Force KDE

def kde_brute_force(points, width, height, bandwidth, grid_spacing):
    """
    Реализует метод прямого перебора (brute force) для оценки плотности на регулярной сетке.
    Для каждой ячейки сетки суммируется вклад от всех точек.
    Параметры:
      points       - список координат (x, y);
      width, height - размеры изображения;
      bandwidth    - параметр сглаживания ядра;
      grid_spacing - размер одной ячейки в пикселях.
    Возвращает двумерный список плотностей density_grid[h][w].
    """
    grid_w = int(width / grid_spacing)
    grid_h = int(height / grid_spacing)
    
    density_grid = [[0.0 for _ in range(grid_w)] for _ in range(grid_h)]
    
    for i in range(grid_h):
        # Центр ячейки по вертикали
        y_center = i * grid_spacing + grid_spacing / 2
        for j in range(grid_w):
            # Центр ячейки по горизонтали
            x_center = j * grid_spacing + grid_spacing / 2
            density = 0.0
            for (px, py) in points:
                dx = x_center - px
                dy = y_center - py
                dist_sq = dx * dx + dy * dy
                density += gaussian_kernel(dist_sq, bandwidth)
            density_grid[i][j] = density
    return density_grid



# Сложность ~O(M * N), где M – число ячеек (grid_w × grid_h), N – число точек.
# Для каждого узла сетки перебираем все точки.



# Шаг 6. Метод 2: Accumulate (с ограничением радиуса)

def kde_accumulate(points, width, height, bandwidth, grid_spacing):
    """
    Метод оценки плотности, при котором для каждой точки определяется
    ограниченная область влияния (до ~3*bandwidth).
    Это позволяет не суммировать вклад точки во все ячейки, а только в те,
    которые лежат внутри заданного радиуса.
    """
    grid_w = int(width / grid_spacing)
    grid_h = int(height / grid_spacing)
    
    density_grid = [[0.0 for _ in range(grid_w)] for _ in range(grid_h)]
    
    # Эффективный радиус влияния
    radius = 3 * bandwidth
    radius_sq = radius * radius
    
    for (px, py) in points:
        center_i = int(py // grid_spacing)
        center_j = int(px // grid_spacing)
        cell_radius = int(math.ceil(radius / grid_spacing))
        
        # Проходим только по ячейкам в пределах радиуса
        for di in range(-cell_radius, cell_radius + 1):
            for dj in range(-cell_radius, cell_radius + 1):
                i = center_i + di
                j = center_j + dj
                # Проверяем, что i, j не вышли за границы
                if 0 <= i < grid_h and 0 <= j < grid_w:
                    # Центр ячейки
                    y_center = i * grid_spacing + grid_spacing / 2
                    x_center = j * grid_spacing + grid_spacing / 2
                    dx = x_center - px
                    dy = y_center - py
                    dist_sq = dx * dx + dy * dy
                    # Если в пределах радиуса, добавляем вклад
                    if dist_sq <= radius_sq:
                        density_grid[i][j] += gaussian_kernel(dist_sq, bandwidth)
    
    return density_grid


'''
Сложность ~O(N * R^2), где N – число точек, R – диаметр области влияния в клетках.
Если grid_spacing достаточно велик, этот метод может работать быстрее,
чем полный перебор, особенно при большом числе точек.

'''


# Шаг 7. Нормализация плотностей

def normalize_density_grid(density_grid):
    """
    Приводит значения плотности в диапазон [0..255] для корректного отображения.
    Возвращает двумерный список тех же размеров, где каждое значение – целое число от 0 до 255.
    """
    min_val = min(min(row) for row in density_grid)
    max_val = max(max(row) for row in density_grid)
    
    if max_val - min_val == 0:
        # Если все значения одинаковые, можно вернуть нули
        return [[0 for _ in row] for row in density_grid]
    
    normalized_grid = []
    for row in density_grid:
        norm_row = [
            int(255 * (val - min_val) / (max_val - min_val))
            for val in row
        ]
        normalized_grid.append(norm_row)
    return normalized_grid


'''
Плотности могут быть очень малыми или большими,
поэтому мы приводим их к 0..255 для 
отображения альфа-канала.
'''


# Шаг 8. Создание изображения тепловой карты


def create_heatmap_image(normalized_grid, grid_spacing, width, height):
    """
    Создаёт полупрозрачное изображение (RGBA), где каждая ячейка сетки закрашена
    в красный цвет с интенсивностью, зависящей от нормализованного значения.
    """
    heatmap = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(heatmap)
    
    grid_h = len(normalized_grid)
    grid_w = len(normalized_grid[0])
    
    for i in range(grid_h):
        for j in range(grid_w):
            intensity = normalized_grid[i][j]
            # Красный цвет, альфа-канал = intensity
            color = (255, 0, 0, intensity)
            
            # Вычисляем координаты ячейки
            x0 = int(j * grid_spacing)
            y0 = int(i * grid_spacing)
            x1 = int((j + 1) * grid_spacing)
            y1 = int((i + 1) * grid_spacing)
            
            # Рисуем прямоугольник
            draw.rectangle([x0, y0, x1, y1], fill=color)
    
    return heatmap

'''
Каждая ячейка сетки отображается как прямоугольник, цвет – красный,
 прозрачность – intensity.
Image.new("RGBA", ...) создаёт пустое полупрозрачное изображение в нужном размере.
'''




# Шаг 9. Наложение тепловой карты на фон


def overlay_heatmap(background, heatmap):
    """
    Накладывает тепловую карту (heatmap) поверх фонового изображения (background)
    путём альфа-композиции.
    """
    return Image.alpha_composite(background, heatmap)
'''

Image.alpha_composite объединяет 
два RGBA-изображения с учётом 
прозрачности (альфа-канала).
'''



# Шаг 10. Сравнение времени работы и запуск полного процесса

import os
from dotenv import load_dotenv

# Загрузка переменных из .env файла
load_dotenv()

def main():


    # Получение параметров из переменных окружения
    image_path = os.getenv("IMAGE_PATH", "simple_screen.png")
    num_walkers = int(os.getenv("NUM_WALKERS", 200))
    points_per_walker = int(os.getenv("POINTS_PER_WALKER", 2000))
    step_size = float(os.getenv("STEP_SIZE", 5.0))
    bandwidth = float(os.getenv("BANDWIDTH", 10.0))
    grid_spacing = float(os.getenv("GRID_SPACING", 10.0))



    # 1. Загрузка фонового изображения
    background, (width, height) = load_background_image(image_path)

    # 2. Генерация данных случайного блуждания
    start_time = time.time()
    points = generate_random_walk_data(width, height, num_walkers, points_per_walker, step_size)
    gen_time = time.time() - start_time
    print(f"Сгенерировано {len(points)} точек за {gen_time:.2f} сек")

    # 3. Вычисление плотности методом brute force
    start_time = time.time()
    density_grid_brute = kde_brute_force(points, width, height, bandwidth, grid_spacing)
    brute_time = time.time() - start_time
    print(f"Brute force завершён за {brute_time:.2f} сек")

    # 4. Вычисление плотности методом accumulate
    start_time = time.time()
    density_grid_acc = kde_accumulate(points, width, height, bandwidth, grid_spacing)
    acc_time = time.time() - start_time
    print(f"Accumulate завершён за {acc_time:.2f} сек")

    # Выбираем, какую карту визуализировать (brute или accumulate)
    # Для наглядности используем accumulate
    density_grid = density_grid_acc

    # 5. Нормализация
    normalized_grid = normalize_density_grid(density_grid)

    # 6. Создание тепловой карты
    heatmap = create_heatmap_image(normalized_grid, grid_spacing, width, height)

    # 7. Наложение тепловой карты на исходное изображение
    result_image = overlay_heatmap(background, heatmap)

    # 8. Сохранение результата
    result_image.save("result_heatmap.png")
    print("Результат сохранён в 'result_heatmap.png'")

    # Сравнение времени
    print(f"\nСравнение времени вычисления KDE:")
    print(f" - Brute force: {brute_time:.2f} сек")
    print(f" - Accumulate:  {acc_time:.2f} сек")

if __name__ == "__main__":
    main()




