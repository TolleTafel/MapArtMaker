import subprocess

def check_dependencies(modules):
    """
    Check if the required modules are installed and install them if they are not.

    :param modules: List of required modules.
    """
    missing_modules = []
    for module in modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)

    if missing_modules:
        print(f"The following modules are not installed: {', '.join(missing_modules)}")
        install = input("Do you want to install them now? (y/n): ")
        if install.lower() == "y":
            for module in missing_modules:
                subprocess.check_call(["python", "-m", "pip", "install", module])
        else:
            print("Please install the missing modules and run the script again.")
            exit(1)

required_modules = ["PIL", "tkinter", "numpy", "os", "json", "tqdm", "math"]

check_dependencies(required_modules)

import tkinter as tk
from tkinter import filedialog
import os
import json
from PIL import Image
import numpy as np
from tqdm import tqdm
import math
import json

with open(r'.\colors.json', 'r') as f:
    colors = json.load(f)
    f.close()
colors = {eval(k): v for k, v in colors.items()}

def delta_e(lab1, lab2):
    """
    Calculate the Delta E color difference between two colors.

    :param lab1: First color in the OKLAB color space.
    :param lab2: Second color in the OKLAB color space.

    :return: Delta E color difference between the two colors.
    """
    dL = lab1[0] - lab2[0]
    a1 = lab1[1]**2
    b1 = lab1[2]**2
    a2 = lab2[1]**2
    b2 = lab2[2]**2
    dC = -2*math.sqrt(a1 + b1)*math.sqrt(a2 + b2) + a1 + b1 + a2 + b2
    da = lab1[1] - lab2[1]
    db = lab1[2] - lab2[2]
    dH = abs(da**2 + db**2 - dC)
    return math.sqrt(dL**2 + dC + dH)

def rgb_to_oklab(rgb):
    """
    Convert RGB color to OKLAB color space.

    :param rgb: RGB color.
    :return: OKLAB color.
    """
    rgb = rgb / 255.0

    lms = np.dot(rgb, [[0.4122214708, 0.5363325362, 0.0514459929], 
                          [0.2119034982, 0.6806995451, 0.1073969566], 
                          [0.0883024619, 0.2817188376, 0.6299787005]])

    lms = np.where(lms > 0.008856451679, np.cbrt(lms), 7.787037037 * lms + 0.1379310345)

    l = 0.2104542553 * lms[..., 0] + 0.7936177850 * lms[..., 1] - 0.0040720468 * lms[..., 2]
    m = 1.9779984951 * lms[..., 0] - 2.4285922050 * lms[..., 1] + 0.4505937099 * lms[..., 2]
    s = 0.0259040371 * lms[..., 0] + 0.7827717662 * lms[..., 1] - 0.8086757660 * lms[..., 2]

    oklab = np.stack([l, m, s], axis=-1)
    return oklab

def closest_color(oklab, colors):
    """
    Find the closest color to the given color in the OKLAB color space.

    :param oklab: OKLAB color to compare.
    :param colors: RGB colors to compare against.
    :return: Closest color to the given color.
    """
    distances = []
    
    for color in colors:
        distances.append(delta_e(oklab, color))
    
    min_distance_index = np.argmin(distances)

    shade_index = (min_distance_index % 3) - 1
    list_keys = list(colors.keys())
    return colors[list_keys[min_distance_index]], shade_index

def get_image_pixels(image_path, colors):
    """
    Get the pixels of the image and convert them to Minecraft blocks.

    :param image_path: The path to the image file.
    :param colors: OKLAB colors to compare against.
    :return: List of Minecraft blocks and their shades.
    """
    pixel_data = []
    shade_data = []

    print("Opening image file...")
    img = Image.open(image_path)
    img = img.convert('RGB')
    pixels = np.array(img)
    pixels = pixels.reshape(-1, 3)
    width, height = img.size

    print("Processing image pixels...")
    total_pixels = width * height
    progress_bar = tqdm(total=total_pixels)

    pixels_oklab = rgb_to_oklab(pixels).tolist()

    for pixel in pixels_oklab:
        closest, shade_index = closest_color(pixel, colors)
        pixel_data.append(closest)
        shade_data.append(shade_index)

        progress_bar.update()
        if progress_bar.n % (total_pixels // 10) == 0:
            progress_bar.refresh()

    progress_bar.close()
    print("Image processing completed.")
    return pixel_data, shade_data, width

def create_mcfunction(pixels, shade, directory, width):
    """
    Create a Minecraft function file with the given pixels.

    :param pixels: The pixels of the image in minecraft blocks.
    :param shade: The shades of the pixels.
    :param directory: The directory to save the function file.
    :param width: The width of the image.
    """
    print("Creating Minecraft function file...")
    x = 0
    y = 0
    if os.path.isfile(directory):
        mode = "w"
    else:
        mode = "x"
    with open(directory, mode) as f:
        f.write(f"fill ~ ~-1 ~-1 ~{width-1} ~-1 ~-1 minecraft:bedrock replace air\n")
        for i, color in enumerate(pixels):
            try:
                if color == "minecraft:light_weighted_pressure_plate":
                    f.write(f"setblock ~{x} ~{shade[i]-2} ~{y} minecraft:stone\n")
                f.write(f"setblock ~{x} ~{shade[i]-1} ~{y} {color}\n")
            except IndexError:
                print(f"IndexError at pixel {i} ({x}, {y}).")
                print(len(shade))
                break
            x += 1
            if x == width:
                x = 0
                y += 1
        f.close()

    print("Minecraft function file created.")

def create_directory_structure(directory):
    """
    Create the directory structure for the data pack.

    :param directory: The directory to create the structure in.
    """
    print("Creating directory structure...")
    mapart_dir = os.path.join(directory, "MapArtMaker")
    os.makedirs(mapart_dir, exist_ok=True)

    data_dir = os.path.join(mapart_dir, "Data")
    os.makedirs(data_dir, exist_ok=True)

    ma_dir = os.path.join(data_dir, "map_art")
    os.makedirs(ma_dir, exist_ok=True)

    functions_dir = os.path.join(ma_dir, "function")
    os.makedirs(functions_dir, exist_ok=True)

    pack_file_path = os.path.join(mapart_dir, "pack.mcmeta")
    if os.path.isfile(pack_file_path):
        print(f"File {pack_file_path} already exists.")
    else:
        pack_data = {
            "pack": {
                "pack_format": 34,
                "description": "Your MapArt. Just yours."
            }
        }
        with open(pack_file_path, 'w') as f:
            json.dump(pack_data, f, indent=2)

    print("Directory structure created.")
    return functions_dir

root = tk.Tk()
root.withdraw()

print("Select image file:")
image_file_path = filedialog.askopenfilename(title="Select an image file to process", filetypes=[("Image files", "*.png *.jpg *.jpeg")])
if not image_file_path:
    print("Terminated Process.")
    exit(1)

print("Selected image file:", image_file_path)

pixels, shade, width = get_image_pixels(image_file_path, colors)

print("Processing image shades...")
shade_chunks = [shade[i:i + width] for i in range(0, len(shade), width)]
for i in range(1, len(shade_chunks)):
    for j in range(width):
        if shade_chunks[i][j] == -1:
            shade_chunks[i][j] = shade_chunks[i-1][j] - 1
        elif shade_chunks[i][j] == 0:
            shade_chunks[i][j] = shade_chunks[i-1][j]
        elif shade_chunks[i][j] == 1:
            shade_chunks[i][j] = shade_chunks[i-1][j] + 1
shade.clear()
for chunk in shade_chunks:
    shade.extend(chunk)

print("Select directory:")
directory_path = filedialog.askdirectory(title="Select a directory for the data pack")
if not os.path.isdir(directory_path):
    print("Terminated Process.")
    exit(1)

print("Selected directory:", directory_path)

data_dir = create_directory_structure(directory_path)

mcfunction_file_path = os.path.join(data_dir, "place.mcfunction")

create_mcfunction(pixels, shade, mcfunction_file_path, width)

print("Operation completed successfully.")
