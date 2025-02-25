import math
import os
from PIL import Image, ImageDraw

class HeatmapService:
    def __init__(self):
        self.raw_data = {}
        self.cache = {}
        self.cache_dir = "cache_images"
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    def store_raw_data(self, page_id, points):
        if page_id not in self.raw_data:
            self.raw_data[page_id] = []
        self.raw_data[page_id].extend(points)

    def generate_heatmap(self, page_id, bandwidth, grid_spacing):
        cache_key = (page_id, bandwidth, grid_spacing)
        if cache_key in self.cache:
            return self.cache[cache_key]

        points = self.raw_data.get(page_id, [])
        if not points:
            return None

        bg_path = os.path.join("images", f"{page_id}.png")
        if not os.path.exists(bg_path):
            return None

        background = Image.open(bg_path).convert("RGBA")
        img_width, img_height = background.size

        grid_w = int(img_width / grid_spacing)
        grid_h = int(img_height / grid_spacing)
        density_grid = [[0.0 for _ in range(grid_w)] for _ in range(grid_h)]

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

        normalized_grid = self.normalize_density_grid(density_grid)

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

        result_image = Image.alpha_composite(background, heatmap)
        out_path = os.path.join(self.cache_dir, f"heatmap_{page_id}_{bandwidth}_{grid_spacing}.png")
        result_image.save(out_path)

        self.cache[cache_key] = out_path
        return out_path

    @staticmethod
    def gaussian_kernel(dist_sq, bandwidth):
        if bandwidth <= 0:
            bandwidth = 1.0
        return math.exp(-dist_sq / (2*bandwidth*bandwidth)) / (2 * math.pi * bandwidth * bandwidth)

    @staticmethod
    def normalize_density_grid(density_grid):
        flat_vals = [val for row in density_grid for val in row]
        min_val = min(flat_vals)
        max_val = max(flat_vals)
        if max_val - min_val == 0:
            return [[0 for _ in row] for row in density_grid]
        norm_grid = []
        for row in density_grid:
            norm_row = [
                int(255*(v - min_val)/(max_val - min_val))
                for v in row
            ]
            norm_grid.append(norm_row)
        return norm_grid