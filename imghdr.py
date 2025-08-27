"""
Module to determine the type of image contained in a file or byte stream.

This is a compatibility module for Python 3.13+ where imghdr was removed.
"""

import struct

def what(file, h=None):
    """Recognize image headers.
    
    The what() function recognizes the type of image contained in a file
    or byte stream, and returns a string describing the image type.
    """
    if h is None:
        if isinstance(file, str):
            f = open(file, 'rb')
            h = f.read(32)
            f.close()
        else:
            location = file.tell()
            h = file.read(32)
            file.seek(location)
    
    if len(h) >= 8:
        if h[:8] == b'\x89PNG\r\n\x1a\n':
            return 'png'
        if h[:4] == b'\xff\xd8\xff':
            return 'jpeg'
        if h[:4] == b'GIF8':
            return 'gif'
        if h[:4] == b'RIFF' and h[8:12] == b'WEBP':
            return 'webp'
        if h[:4] == b'BM':
            return 'bmp'
        if h[:4] == b'\x00\x00\x01\x00':
            return 'ico'
        if h[:4] == b'\x00\x00\x02\x00':
            return 'cur'
        if h[:4] == b'\x00\x00\x01\x00':
            return 'tiff'
    
    return None