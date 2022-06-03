import logging
import pickle

from PIL import Image
from sklearn import svm


class DeCaptcha:
    def __init__(self, length=6):
        self.__clf = svm.NuSVC()
        self.__length = length
        self.__is_active = False
        self.__BIN_TABLE = [0] * 140 + [1] * 116

    def __points_collect(self, bin_image, visited, x, y, points):
        for step_x in range(-1, 2):
            for step_y in range(-1, 2):
                i = x + step_x
                j = y + step_y
                if 0 <= i < bin_image.width and 0 <= j < bin_image.height:
                    if visited[i][j] == 0 and bin_image.getpixel((i, j)) == 0:
                        visited[i][j] = 1
                        points.append([i, j])
                        self.__points_collect(bin_image, visited, i, j, points)

    def __remove_noise_point(self, bin_image):
        width = bin_image.width
        height = bin_image.height
        visited = [[0 for _ in range(height)] for _ in range(width)]
        for i in range(width):
            bin_image.putpixel((i, 0), 1)
            bin_image.putpixel((i, height - 1), 1)
        for j in range(height):
            bin_image.putpixel((0, j), 1)
            bin_image.putpixel((width - 1, j), 1)
        for i in range(width):
            for j in range(height):
                if visited[i][j] == 0 and bin_image.getpixel((i, j)) == 0:
                    points = []
                    self.__points_collect(bin_image, visited, i, j, points)
                    if 1 <= len(points) <= 3:
                        for x, y in points:
                            bin_image.putpixel((x, y), 1)

    def __get_char_images(self, image):
        char_images = []
        for i in range(self.__length):
            x = 25 + i * (8 + 10)
            y = 15
            child_img = image.crop((x, y, x + 8, y + 10))
            char_images.append(child_img)
        return char_images

    def __preprocess(self, image):
        gray_image = image.convert('L')
        bin_image = gray_image.point(self.__BIN_TABLE, '1')
        self.__remove_noise_point(bin_image)
        return bin_image

    def __get_feature(self, image):
        width, height = image.size
        pixel_cnt_list = []
        for y in range(height):
            pix_cnt_x = 0
            for x in range(width):
                if image.getpixel((x, y)) == 0:
                    pix_cnt_x += 1
            pixel_cnt_list.append(pix_cnt_x)
        for x in range(width):
            pix_cnt_y = 0
            for y in range(height):
                if image.getpixel((x, y)) == 0:
                    pix_cnt_y += 1
            pixel_cnt_list.append(pix_cnt_y)
        return pixel_cnt_list

    def set_length(self, length):
        self.__length = length

    def train(self, captcha_text_list):
        if not isinstance(captcha_text_list, list):
            logging.error(
                'captcha_text_list must be list like [[\'./image1.png\', \'WSA23D\'], \
                [\'./image2.png\', \'223S2S\']]!')
            return False
        x = []
        y = []
        for captcha_path, captcha_text in captcha_text_list:
            image = self.__preprocess(Image.open(captcha_path))
            char_images = self.__get_char_images(image)
            for i in range(self.__length):
                feature = self.__get_feature(char_images[i])
                digit = captcha_text[i]
                x.append(feature)
                y.append(digit)
        self.__clf.fit(x, y)
        self.__is_active = True
        return True

    def decode(self, image):
        if not isinstance(image, Image.Image):
            logging.error('image must be instance of Image.Image in PIL!')
            return
        if not self.__is_active:
            logging.error('train or load_model first!')
            return
        image = self.__preprocess(image)
        char_images = self.__get_char_images(image)
        features = []
        for i in range(self.__length):
            features.append(self.__get_feature(char_images[i]))
        result = self.__clf.predict(features)
        text = ''.join(result)
        return text

    def load_model(self, filename):
        if not isinstance(filename, str):
            logging.error('filename must be a string!')
            return
        with open(filename, 'rb') as fid:
            self.__clf = pickle.load(fid)
            self.__is_active = True

    def dump_model(self, filename):
        if not isinstance(filename, str):
            logging.error('filename must be a string!')
            return
        with open(filename, 'wb') as fid:
            pickle.dump(self.__clf, fid)
