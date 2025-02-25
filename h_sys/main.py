import json
import math
import random
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse as urlparse
from PIL import Image, ImageDraw  # Стандартной библиотекой PIL не является, но часто идёт как Pillow.
                                 # Если Pillow тоже считать "внешней" – тогда придётся писать свой модуль
                                 # для работы с изображениями. Здесь оставим для наглядности.

##############################################################################
# МОДУЛЬ БИЗНЕС-ЛОГИКИ: работа с данными, генерация тепловых карт
##############################################################################

class HeatmapService:
    def __init__(self):
        """
        Инициализация сервиса. Можно подключиться к БД, загрузить кэш и т.д.
        """
        # Для простоты храним данные в памяти:
        # - Ключ: идентификатор (page_id) + параметры (bandwidth, grid, etc.)
        # - Значение: путь к готовому файлу с тепловой картой
        self.cache = {}

        # Храним "сырые" данные взглядов тоже в памяти (page_id -> список точек)
        self.raw_data = {}

        # Папка для сохранения сгенерированных тепловых карт
        self.cache_dir = "cache_images"
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    def store_raw_data(self, page_id, points):
        """
        Сохранить сырые данные (список координат) для заданной страницы page_id.
        Здесь можно было бы обращаться к БД.
        """
        if page_id not in self.raw_data:
            self.raw_data[page_id] = []
        self.raw_data[page_id].extend(points)  # добавляем точки

    def generate_heatmap(self, page_id, bandwidth, grid_spacing):
        """
        Генерация тепловой карты (простейший вариант) для указанных параметров.
        Возвращает путь к PNG-файлу с тепловой картой.
        """
        # Проверяем кэш
        cache_key = f"{page_id}_{bandwidth}_{grid_spacing}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Если нет в кэше, нужно сгенерировать
        points = self.raw_data.get(page_id, [])
        if not points:
            # Нет данных
            return None

        # Допустим, у нас есть фоновое изображение (page_id.png)
        bg_path = f"{page_id}.png"
        if not os.path.exists(bg_path):
            # В реальном решении нужно вернуть ошибку или использовать заглушку
            return None

        background = Image.open(bg_path).convert("RGBA")
        img_width, img_height = background.size

        # 1) Формируем сетку
        grid_w = int(img_width / grid_spacing)
        grid_h = int(img_height / grid_spacing)
        density_grid = [[0.0 for _ in range(grid_w)] for _ in range(grid_h)]

        # 2) Простейший brute-force KDE (без оптимизаций, только для демонстрации)
        for i in range(grid_h):
            y_center = i * grid_spacing + grid_spacing / 2
            for j in range(grid_w):
                x_center = j * grid_spacing + grid_spacing / 2
                density = 0.0
                for (px, py) in points:
                    dx = x_center - px
                    dy = y_center - py
                    dist_sq = dx*dx + dy*dy
                    density += self.gaussian_kernel(dist_sq, bandwidth)
                density_grid[i][j] = density

        # 3) Нормализация
        normalized_grid = self.normalize_density_grid(density_grid)

        # 4) Создаём heatmap-слой
        heatmap = Image.new("RGBA", (img_width, img_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(heatmap)
        for i in range(grid_h):
            for j in range(grid_w):
                intensity = normalized_grid[i][j]
                color = (255, 0, 0, intensity)
                x0 = int(j * grid_spacing)
                y0 = int(i * grid_spacing)
                x1 = int((j+1) * grid_spacing)
                y1 = int((i+1) * grid_spacing)
                draw.rectangle([x0, y0, x1, y1], fill=color)


# 5) Альфа-композиция
        result_image = Image.alpha_composite(background, heatmap)

        # 6) Сохраняем в файл (кэш)
        out_path = os.path.join(self.cache_dir, f"heatmap_{cache_key}.png")
        result_image.save(out_path)

        self.cache[cache_key] = out_path
        return out_path

    @staticmethod
    def gaussian_kernel(dist_sq, bandwidth):
        """
        Гауссово ядро.
        """
        if bandwidth <= 0:
            bandwidth = 1.0
        return math.exp(-dist_sq / (2*bandwidth*bandwidth)) / (2 * math.pi * bandwidth * bandwidth)

    @staticmethod
    def normalize_density_grid(density_grid):
        """
        Нормируем значения в диапазон [0..255].
        """
        flat_vals = [val for row in density_grid for val in row]
        min_val = min(flat_vals)
        max_val = max(flat_vals)
        if max_val - min_val == 0:
            return [[0 for _ in row] for row in density_grid]
        norm = []
        for row in density_grid:
            norm.append([
                int(255*(v - min_val)/(max_val - min_val)) for v in row
            ])
        return norm
    




  

##############################################################################
# МОДУЛЬ ВЕБ-СЕРВЕРА: принимаем HTTP-запросы, вызываем бизнес-логику
##############################################################################

class SimpleRequestHandler(BaseHTTPRequestHandler):
    # Создаём единый экземпляр сервиса (HeatmapService)
    # В реальном решении лучше инициализировать в main() и передавать сюда,
    # но для демонстрации сделаем статическую переменную.
    service = HeatmapService()

    def do_GET(self):
        """
        Обработка GET-запросов. Например, запрос тепловой карты.
        Пример: /heatmap?page_id=somepage&bandwidth=10&grid=15
        """
        parsed_url = urlparse.urlparse(self.path)
        query = urlparse.parse_qs(parsed_url.query)

        if parsed_url.path == "/heatmap":
            page_id = query.get("page_id", ["unknown"])[0]
            bandwidth = float(query.get("bandwidth", [10])[0])
            grid = float(query.get("grid", [15])[0])

            # Генерируем тепловую карту
            result_path = self.service.generate_heatmap(page_id, bandwidth, grid)
            if result_path and os.path.exists(result_path):
                # Отдаём файл (image/png)
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.end_headers()
                with open(result_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                # Нет данных или ошибка
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Heatmap not found or no data.")
        else:
            # Неподдерживаемый путь
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def do_POST(self):
        """
        Обработка POST-запросов. Например, загрузка новых данных взглядов.
        Пример: /upload_data?page_id=somepage
        Тело запроса (JSON): {"points": [[x1,y1],[x2,y2],...]}
        """
        parsed_url = urlparse.urlparse(self.path)
        query = urlparse.parse_qs(parsed_url.query)

        if parsed_url.path == "/upload_data":
            page_id = query.get("page_id", ["unknown"])[0]

            content_length = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_length)
            try:
                data = json.loads(post_body.decode("utf-8"))
                points = data.get("points", [])
                # Сохраняем точки
                self.service.store_raw_data(page_id, points)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Data uploaded successfully.")
            except Exception as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(f"Error parsing data: {e}".encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")


def run_server(host="0.0.0.0", port=8080):
    """
    Запуск простого HTTP-сервера.
    """
    httpd = HTTPServer((host, port), SimpleRequestHandler)
    print(f"Server started at http://{host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    run_server()

























