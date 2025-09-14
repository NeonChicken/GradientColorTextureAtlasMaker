import os
import glob
from PIL import Image, ImageDraw
import random
import math

def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple"""
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def rgb_distance(color1, color2):
    """Calculate Euclidean distance between two RGB colors"""
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(color1, color2)))

def find_neighbors(target_color, colors, max_neighbors=3, min_distance=2):
    """Find 1-3 nearest neighbor colors with minimum distance spacing"""
    distances = [(rgb_distance(target_color, color), color) for color in colors if color != target_color]
    distances.sort()

    # Select neighbors with spacing - skip closer ones to get more variety
    selected = []
    start_index = min_distance  # Start from at least 2-4 positions away
    for i in range(start_index, min(start_index + max_neighbors, len(distances))):
        if i < len(distances):
            selected.append(distances[i][1])

    return selected

def get_lightest_darkest(colors):
    """Find the lightest and darkest colors based on luminance"""
    def luminance(color):
        r, g, b = color
        return 0.299 * r + 0.587 * g + 0.114 * b

    sorted_colors = sorted(colors, key=luminance)
    return sorted_colors[0], sorted_colors[-1]  # darkest, lightest

def create_gradient(colors, width, height, vertical=True):
    """Create a gradient image from a list of colors"""
    img = Image.new('RGB', (width, height))
    pixels = []

    if len(colors) == 1:
        # Solid color
        pixels = [colors[0]] * (width * height)
    else:
        # Multi-color gradient
        for y in range(height):
            for x in range(width):
                # Calculate position in gradient (0.0 to 1.0)
                if vertical:
                    pos = y / (height - 1) if height > 1 else 0
                else:
                    pos = x / (width - 1) if width > 1 else 0

                # Find which segment of the gradient we're in
                segment_size = 1.0 / (len(colors) - 1)
                segment = int(pos / segment_size)
                segment = min(segment, len(colors) - 2)

                # Local position within the segment (0.0 to 1.0)
                local_pos = (pos - segment * segment_size) / segment_size

                # Interpolate between the two colors
                color1 = colors[segment]
                color2 = colors[segment + 1]

                r = int(color1[0] + (color2[0] - color1[0]) * local_pos)
                g = int(color1[1] + (color2[1] - color1[1]) * local_pos)
                b = int(color1[2] + (color2[2] - color1[2]) * local_pos)

                pixels.append((r, g, b))

    img.putdata(pixels)
    return img

def process_hex_file(hex_file_path):
    """Process a single .hex file and create texture atlas"""
    # Read hex colors
    with open(hex_file_path, 'r') as f:
        hex_colors = [line.strip() for line in f if line.strip()]

    # Convert to RGB
    rgb_colors = [hex_to_rgb(hex_color) for hex_color in hex_colors if len(hex_color) == 6]

    if not rgb_colors:
        print(f"No valid colors found in {hex_file_path}")
        return

    # Create 2048x2048 canvas
    canvas = Image.new('RGB', (2048, 2048), (255, 255, 255))

    # MAIN gradient width (narrower than before)
    main_gradient_width = 100

    # Calculate space for bottom gradients first
    gradient_start_y = 600  # Reserve top 600px for squares
    available_gradient_height = 2048 - gradient_start_y
    gradient_height = available_gradient_height // 2  # Two rows

    # Calculate width available for gradients and squares - must be exactly the same
    total_content_width = 2048 - main_gradient_width
    num_gradients = 11  # Leave space for the first special gradient
    gradient_width = total_content_width // (num_gradients + 1)  # +1 for the first gradient

    # Make sure gradients fill exactly the available width with no remainder
    total_gradient_width = gradient_width * (num_gradients + 1)

    # Calculate optimal square arrangement using EXACT same width as gradients
    num_colors = len(rgb_colors)
    available_width_for_squares = total_gradient_width  # Exactly same width as gradients

    # Use more aggressive column calculation to make bigger squares
    target_square_size = 100  # Aim for bigger squares
    max_cols = available_width_for_squares // target_square_size
    grid_cols = min(max_cols, num_colors)  # Don't exceed number of colors

    # If we can fit all colors in one row, do it, otherwise calculate optimal grid
    if grid_cols >= num_colors:
        grid_cols = num_colors
        grid_rows = 1
    else:
        grid_rows = int(math.ceil(num_colors / grid_cols))

    # Calculate square width to perfectly fill the available width
    # Make each row fill exactly total_gradient_width
    square_width = total_gradient_width // grid_cols
    remaining_width_per_row = total_gradient_width % grid_cols

    # Calculate square height
    square_height = min(square_width, gradient_start_y // grid_rows)

    # Calculate actual grid dimensions
    grid_height = grid_rows * square_height

    # Draw color grid (squares) with perfect alignment
    for i, color in enumerate(rgb_colors):
        row = i // grid_cols
        col = i % grid_cols

        # Calculate position
        x = col * square_width
        y = row * square_height

        # Calculate width for this square - add extra pixel to first squares if needed
        current_square_width = square_width
        if col < remaining_width_per_row:
            current_square_width += 1
            # Adjust x position for squares that come after the wider ones
            x += col
        else:
            # Adjust x position for squares that come after the wider ones
            x += remaining_width_per_row

        # Create color square
        square = Image.new('RGB', (current_square_width, square_height), color)
        canvas.paste(square, (x, y))

    # MAIN gradient extends from gradients to the very right edge
    actual_main_gradient_width = 2048 - total_gradient_width
    main_gradient = create_gradient(rgb_colors, actual_main_gradient_width, 2048, vertical=True)
    canvas.paste(main_gradient, (total_gradient_width, 0))

    # First gradient: lightest to darkest
    darkest, lightest = get_lightest_darkest(rgb_colors)
    first_gradient = create_gradient([lightest, darkest], gradient_width, gradient_height, vertical=True)
    canvas.paste(first_gradient, (0, gradient_start_y))

    # First row of bottom gradients: neighboring colors with more spacing
    for i in range(num_gradients):
        # Pick a random starting color
        start_color = random.choice(rgb_colors)
        neighbors = find_neighbors(start_color, rgb_colors, random.randint(1, 3), min_distance=random.randint(2, 4))

        if neighbors:
            gradient_colors = [start_color] + neighbors[:random.randint(1, min(2, len(neighbors)))]
        else:
            gradient_colors = [start_color]

        gradient = create_gradient(gradient_colors, gradient_width, gradient_height, vertical=True)
        canvas.paste(gradient, ((i + 1) * gradient_width, gradient_start_y))

    # Second row of bottom gradients: random colors
    for i in range(num_gradients + 1):  # Include all positions
        # 2-3 random colors
        num_random_colors = random.randint(2, 3)
        gradient_colors = random.sample(rgb_colors, min(num_random_colors, len(rgb_colors)))

        gradient = create_gradient(gradient_colors, gradient_width, gradient_height, vertical=True)
        canvas.paste(gradient, (i * gradient_width, gradient_start_y + gradient_height))

    # Save the image
    base_name = os.path.splitext(os.path.basename(hex_file_path))[0]
    output_path = f"{base_name}-cta.png"
    canvas.save(output_path)
    print(f"Created texture atlas: {output_path}")

def main():
    """Process all .hex files in the current directory"""
    hex_files = glob.glob("*.hex")

    if not hex_files:
        print("No .hex files found in the current directory")
        return

    for hex_file in hex_files:
        print(f"Processing {hex_file}...")
        process_hex_file(hex_file)

if __name__ == "__main__":
    main()