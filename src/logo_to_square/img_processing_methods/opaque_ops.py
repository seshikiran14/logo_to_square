from PIL import Image


def get_bg_color(im):  # gets the background colour of the and rgb image
    px = im.load()
    width, height = im.size

    # Clamp corner sample offsets so tiny images don't raise index errors.
    left_x = min(4, max(0, width - 1))
    right_x = max(0, width - 6)
    top_y = min(4, max(0, height - 1))
    bottom_y = max(0, height - 6)

    top_left = px[left_x, top_y]
    top_right = px[right_x, top_y]
    bottom_left = px[left_x, bottom_y]
    bottom_right = px[right_x, bottom_y]

    avg_color = get_avg_color(top_left, top_right, bottom_left, bottom_right)
    return avg_color


def get_avg_color(tl, tr, bl, br):  # calcluates the average value of "rgb" of the corner pixels
    sum_of_all = [sum(tup) for tup in zip(tl, tr, bl, br)]
    avg_rgb = tuple(item // 4 for item in sum_of_all)
    return avg_rgb


def expand_to_square(img, background_color):  # converts an image to sqaure
    width, height = img.size
    if width == height:
        return img
    if width > height:
        result = Image.new(img.mode, (width, width), background_color)
        result.paste(img, (0, (width - height) // 2))
        return result
    result = Image.new(img.mode, (height, height), background_color)
    result.paste(img, ((height - width) // 2, 0))
    return result
