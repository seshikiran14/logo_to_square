from PIL import Image


def resize_method(img, target_size):
    """Resize image so its longest side matches target_size."""
    width, height = img.size
    if width == height == target_size:
        return img

    if width >= height:
        new_width = int(target_size)
        new_height = max(1, int((height / width) * target_size))
    else:
        new_height = int(target_size)
        new_width = max(1, int((width / height) * target_size))

    return img.resize((new_width, new_height), Image.Resampling.LANCZOS)




                      
           
           
           