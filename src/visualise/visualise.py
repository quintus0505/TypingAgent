# -*- coding: utf-8 -*-

import numpy as np
import queue
import cv2
import csv
import pprint
from tqdm import tqdm
from PIL import ImageFont, ImageDraw, Image
from data.kbd1k.data_utils.user_config import keyboard_index, keyboard_name, CHI21_KEYS
from data.kbd1k.data_utils.labeling import get_imgpath, load_dataframe
import os.path as osp
import os

pp = pprint.PrettyPrinter(indent=4)

# global
# from the image device.png
start_x = 563
start_y = 1956
key_width = 131
key_height = 230

# device image
# device_img = "./data/images/device.png"
# device_img = "./data/images/android.png"
# device_img = "./data/images/swiftkey.png"
# device_img = "./data/images/grammarly.png"
# device_img = "./data/images/designkey.png"

# video fps
fps = 50

# eye color
eye_rgb = (0, 255, 0)  # (255, 0, 0)

# finger color
finger_rgb = (255, 0, 0)  # (0, 255, 0)

# agent radius
radius = 40

# Transparency factor
alpha = 0.7

fontpath = "./src/visualise/Arial.ttf"
font = ImageFont.truetype(fontpath, 60)

def read_data_from_csv(filename):
    """ Reads test data stored in csv file.
        CSV Structure: ["model time", "agent loc x", "agent loc y", "action x", "action y", "type"]

        Args:
            filename : name of csv file.

        Returns:
            data : list of data in csv file excluding the header row.
    """
    with open(filename, 'rU') as f:
        reader = csv.reader(f, delimiter=',')
        data = list(list(line) for line in reader)
        data = data[1:]
        return data


# def get_imgpath(keyboard_name, dataset_dir=DEFAULT_KEYBOARD_DATASET_DIR, number_row=False):
#     """
#     Get image path based on given keyboard name and dataset dir (/keyboard_dataset)
#     :param keyboard_name:
#     :param dataset_dir:
#     :param number_row:
#     :return:
#     """
#     # TODO: modify when there is a csv for keyboard name and index
#     assert osp.exists(dataset_dir), "No dataset under current dataset dir"
#     file_names = os.listdir(dataset_dir)
#
#     # get img considering w/o light theme
#     if not number_row:
#         img_name_suffixes = ['_0_1_1_1_1.png', '_0_0_1_1_1.png', '_0_1_0_1_1.png', '_0_0_0_1_1.png', '_0_1_1_0_1.png',
#                              '_0_0_1_0_1.png', '_0_1_0_0_1.png', '_0_0_0_0_1.png']
#     else:
#         img_name_suffixes = ['_0_1_1_1_3.png', '_0_0_1_1_3.png', '_0_1_0_1_3.png', '_0_0_0_1_3.png', '_0_1_1_0_3.png',
#                              '_0_0_1_0_3.png', '_0_1_0_0_3.png', '_0_0_0_0_3.png']
#     for img_name_suffix in img_name_suffixes:
#         img_name = keyboard_index[keyboard_name] + img_name_suffix
#         if img_name in file_names:
#             return dataset_dir + '/' + img_name
#     raise Exception(
#         "{} {} does not have a version with border and uppercase".format(keyboard_name, keyboard_index[keyboard_name]))


def interp_test_data(data):
    """ Interpolates the data according to the specified fps

        Args:
            data : list of test data of shape :
            ["model time", "agent loc x", "agent loc y", "action x", "action y", "type"].

        Returns:
            itrp_data : list of interpolated data.
    """
    # interpolation interval = (1000 / fps) since 1 sec = 1000 ms
    interp_ms = 1000 / fps

    ####int(round(float(data[i][0])/interp_ms)*interp_ms)
    # rounding off model times to nearest interp_ms.
    model_time = [int(interp_ms * round(float(val[0]) / interp_ms)) for val in data]
    agent_loc_x = [int(val[1]) for val in data]
    agent_loc_y = [int(val[2]) for val in data]
    action_x = [val[3] for val in data]
    action_y = [val[4] for val in data]
    itrp_data = []

    # arranging model time. +1 to include last time.
    model_time_itrp = np.arange(0, model_time[-1] + 1, interp_ms)
    # interpolate agent loc x wrt model time.
    agent_loc_x_itrp = np.interp(model_time_itrp, model_time, agent_loc_x)
    # interpolate agent loc y wrt model time.
    agent_loc_y_itrp = np.interp(model_time_itrp, model_time, agent_loc_y)

    # copying the action where it was present originally
    for i in tqdm(range(len(model_time_itrp))):
        action_x_itrp = ""
        action_y_itrp = ""
        if model_time_itrp[i] in model_time:
            idx = model_time.index(model_time_itrp[i])
            action_x_itrp = action_x[idx]
            action_y_itrp = action_y[idx]
        itrp_data.append([model_time_itrp[i], agent_loc_x_itrp[i], agent_loc_y_itrp[i], action_x_itrp, action_y_itrp])
    return itrp_data


def lerp(v0, v1, i):
    return v0 + i * (v1 - v0)


def interp_cubic_test_data(data):
    """ Interpolates the data according to the specified fps

        Args:
            data : list of test data of shape :
            ["model time", "agent loc x", "agent loc y", "action x", "action y", "type"].

        Returns:
            itrp_data : list of interpolated data.
    """
    # interpolation interval = (1000 / fps) since 1 sec = 1000 ms
    interp_ms = 1000 / fps

    ####int(round(float(data[i][0])/interp_ms)*interp_ms)
    # rounding off model times to nearest interp_ms.
    model_time = [int(interp_ms * round(float(val[0]) / interp_ms)) for val in data]
    agent_loc_x = [int(val[1]) for val in data]
    agent_loc_y = [int(val[2]) for val in data]
    action_x = [val[3] for val in data]
    action_y = [val[4] for val in data]
    itrp_data = []

    # arranging model time. +1 to include last time.

    model_time_itrp = []  # np.arange(0, model_time[-1] + 1, interp_ms)
    # interpolate agent loc x wrt model time.
    agent_loc_x_itrp = []  # np.interp(model_time_itrp, model_time, agent_loc_x)
    # interpolate agent loc y wrt model time.
    agent_loc_y_itrp = []  # np.interp(model_time_itrp, model_time, agent_loc_y)

    # TODO: doing a hack job here due to deadline. Future work to clean up the entire visualisation code.
    for i in range(len(model_time) - 1):
        x0 = agent_loc_x[i]
        y0 = agent_loc_y[i]

        x1 = agent_loc_x[i + 1]
        y1 = agent_loc_y[i + 1]

        time_diff = model_time[i + 1] - model_time[i]
        n = int(time_diff / interp_ms)

        print(n)
        print(i)
        print(n*i)
        points = [(lerp(x0, x1, ((1. / n * i)) ** 3), lerp(y0, y1, ((1. / n * i)) ** 3)) for i in range(n + 1)]
        points = points[1:]
        t = model_time[i] + interp_ms
        for row in points:
            model_time_itrp.append(t)
            agent_loc_x_itrp.append(row[0])
            agent_loc_y_itrp.append(row[1])
            t += interp_ms

    model_time_itrp.append(model_time[-1])
    agent_loc_x_itrp.append(agent_loc_x[-1])
    agent_loc_y_itrp.append(agent_loc_y[-1])

    for i in tqdm(range(len(model_time_itrp))):
        action_x_itrp = ""
        action_y_itrp = ""
        if model_time_itrp[i] in model_time:
            idx = model_time.index(model_time_itrp[i])
            action_x_itrp = action_x[idx]
            action_y_itrp = action_y[idx]
        itrp_data.append([model_time_itrp[i], agent_loc_x_itrp[i], agent_loc_y_itrp[i], action_x_itrp, action_y_itrp])
    return itrp_data


def xy_to_key(row, col):
    """ given row and col returns the respective character.

        Args:
            row : index of row.
            col : index of col.

        Returns:
            keys[row][col] : character corresponding to row and col
    """
    row, col = (int(row)%4), (int(col)%11)
    keys = [['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p', 'å'],
            ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', 'ö', 'ä'],
            ['-', '-', 'z', 'x', 'c', 'v', 'b', 'n', 'm', '<', '<'],
            ['-', '-', '-', ' ', ' ', ' ', ' ', ' ', '>', '>', '>']]  # < : backspace, > : enter
    return keys[row][col]


def xy_to_pixels(row, col, key_dict):
    """ given row and col returns the pixel x and y for the device.

        Args:
            row : index of row.
            col : index of col.

        Returns:
            x : x pixel in the device
            y : y pixel in the device
    """
    if row < 0:
        return 540, 130
    char_xy = {'1': [5.25, 1271.0, 111.75, 1114.0], '2': [111.75, 1271.0, 218.25, 1114.0], '3': [218.25, 1271.0, 324.75, 1114.0], '4': [324.75, 1271.0, 431.25, 1114.0], '5': [431.25, 1271.0, 537.75, 1114.0], '6': [537.75, 1271.0, 644.25, 1114.0], '7': [644.25, 1271.0, 750.75, 1114.0], '8': [750.75, 1271.0, 857.25, 1114.0], '9': [857.25, 1271.0, 963.75, 1114.0], '0': [963.75, 1271.0, 1070.25, 1114.0], 'q': [6.25, 1425.0, 112.75, 1268.0], 'w': [112.75, 1425.0, 219.25, 1268.0], 'e': [219.25, 1425.0, 325.75, 1268.0], 'r': [325.75, 1425.0, 432.25, 1268.0], 't': [432.25, 1425.0, 538.75, 1268.0], 'y': [538.75, 1425.0, 645.25, 1268.0], 'u': [645.25, 1425.0, 751.75, 1268.0], 'i': [751.75, 1425.0, 858.25, 1268.0], 'o': [858.25, 1425.0, 964.75, 1268.0], 'p': [964.75, 1425.0, 1071.25, 1268.0], 'a': [59.75, 1582.0, 166.25, 1425.0], 's': [166.25, 1582.0, 272.75, 1425.0], 'd': [272.75, 1582.0, 379.25, 1425.0], 'f': [379.25, 1582.0, 485.75, 1425.0], 'g': [485.75, 1582.0, 592.25, 1425.0], 'h': [592.25, 1582.0, 698.75, 1425.0], 'j': [698.75, 1582.0, 805.25, 1425.0], 'k': [805.25, 1582.0, 911.75, 1425.0], 'l': [911.75, 1582.0, 1018.25, 1425.0], 'z': [164.25, 1744.5, 270.75, 1587.5], 'x': [270.75, 1744.5, 377.25, 1587.5], 'c': [377.25, 1744.5, 483.75, 1587.5], ' ': [377.25, 1901.5, 803.25, 1744.5], 'v': [483.75, 1744.5, 590.25, 1587.5], 'b': [590.25, 1744.5, 696.75, 1587.5], 'n': [696.75, 1744.5, 803.25, 1587.5], 'm': [803.25, 1744.5, 909.75, 1587.5], '-': [803.25, 1901.5, 909.75, 1744.5], '<': [909.75, 1744.5, 1080, 1587.5], '>': [909.75, 1901.5, 1080, 1744.5]}
    swiftkey = {'q': [10, 1242, 116, 1378], 'w': [116, 1242, 222, 1378], 'e': [222, 1242, 328, 1378], 'r': [328, 1242, 434, 1378], 't': [434, 1242, 540, 1378], 'y': [540, 1242, 646, 1378], 'u': [646, 1242, 752, 1378], 'i': [752, 1242, 858, 1378], 'o': [858, 1242, 964, 1378], 'p': [964, 1242, 1070, 1378], 'a': [64, 1377, 170, 1513], 's': [170, 1377, 276, 1513], 'd': [276, 1377, 382, 1513], 'f': [382, 1377, 488, 1513], 'g': [488, 1377, 594, 1513], 'h': [594, 1377, 700, 1513], 'j': [700, 1377, 806, 1513], 'k': [806, 1377, 912, 1513], 'l': [912, 1377, 1018, 1513], 'z': [174, 1514, 280, 1650], 'x': [280, 1514, 386, 1650], 'c': [386, 1514, 492, 1650], 'v': [492, 1514, 598, 1650], 'b': [598, 1514, 704, 1650], 'n': [704, 1514, 810, 1650], 'm': [810, 1514, 916, 1650], '<': [916, 1514, 1080, 1650], ' ': [330, 1650, 804, 1785], '>': [916, 1650, 1080, 1785], '-': [804, 1650, 916, 1785]}
    designkey = {'q': [18, 1248, 121, 1380], 'w': [121, 1248, 224, 1380], 'e': [225, 1248, 328, 1380], 'r': [328, 1248, 431, 1380], 't': [432, 1248, 535, 1380], 'y': [535, 1248, 638, 1380], 'u': [639, 1248, 742, 1380], 'i': [742, 1248, 845, 1380], 'o': [846, 1248, 949, 1380], 'p': [949, 1248, 1052, 1380], 'a': [73, 1384, 176, 1516], 's': [176, 1384, 279, 1516], 'd': [280, 1384, 383, 1516], 'f': [383, 1384, 486, 1516], 'g': [487, 1384, 590, 1516], 'h': [590, 1384, 693, 1516], 'j': [694, 1384, 797, 1516], 'k': [797, 1384, 900, 1516], 'l': [901, 1384, 1004, 1516], 'z': [175, 1512, 278, 1644], 'x': [278, 1512, 381, 1644], 'c': [382, 1512, 485, 1644], 'v': [485, 1512, 588, 1644], 'b': [589, 1512, 692, 1644], 'n': [692, 1512, 795, 1644], 'm': [796, 1512, 899, 1644], '<': [899, 1512, 1080, 1644], ' ': [258, 1644, 789, 1776], '>': [911, 1644, 1080, 1776], '-': [789, 1644, 911, 1776]}
    grammaly = {'q': [5, 1150, 112, 1312], 'w': [112, 1150, 219, 1312], 'e': [219, 1150, 326, 1312], 'r': [326, 1150, 433, 1312], 't': [433, 1150, 540, 1312], 'y': [540, 1150, 647, 1312], 'u': [647, 1150, 754, 1312], 'i': [754, 1150, 861, 1312], 'o': [861, 1150, 968, 1312], 'p': [968, 1150, 1075, 1312], 'a': [59, 1313, 166, 1475], 's': [166, 1313, 273, 1475], 'd': [273, 1313, 380, 1475], 'f': [380, 1313, 487, 1475], 'g': [487, 1313, 594, 1475], 'h': [594, 1313, 701, 1475], 'j': [701, 1313, 808, 1475], 'k': [808, 1313, 915, 1475], 'l': [915, 1313, 1022, 1475], 'z': [166, 1472, 273, 1634], 'x': [273, 1472, 380, 1634], 'c': [380, 1472, 487, 1634], 'v': [487, 1472, 594, 1634], 'b': [594, 1472, 701, 1634], 'n': [701, 1472, 808, 1634], 'm': [808, 1472, 915, 1634], '-': [808, 1472, 915, 1634], '<': [915, 1472, 1080, 1634],' ': [373, 1634, 816, 1796],  '>': [934, 1634, 1080, 1796], '-': [816, 1634, 934, 1796]}
    char_xy = key_dict
    # x = start_x + float(col) * key_width
    # y = start_y + float(row) * key_height
    key = xy_to_key(row, col)
    if key not in char_xy:
        key = '-'
    x = char_xy[key][0] + (char_xy[key][2] - char_xy[key][0]) / 2
    y = char_xy[key][1] + (char_xy[key][3] - char_xy[key][1]) / 2
    x = int(x)
    y = int(y)
    return x, y


def draw_agent(img, loc_x, loc_y, rgb, key_dict):
    """ draw agent location on the device with given color.

        Args:
            img : cv2 read image of device.
            loc_x : col of the agent.
            loc_y : row of the agent.
            rgb : (r,g,b) tuple of rgb color

        Returns:
            agent_drawn_img : image with agent drawn
            x : x pixel of agent in the device
            y : y pixel of agent in the device
    """
    x, y = xy_to_pixels(loc_x, loc_y, key_dict)
    agent_drawn_img = cv2.circle(img, (int(x), int(y)), radius, rgb, -1)
    return agent_drawn_img, int(x), int(y)


def draw_agent_points(img, trail_data, rgb, vision, key_dict):
    """ draw agent location on the device with given color.

        Args:
            img : cv2 read image of device.
            trail_data : data of trail data of the agent
            rgb : (r,g,b) tuple of rgb color
            vision: boolean for plotting vision point

        Returns:
            agent_drawn_img : image with agent drawn
            x : x pixel of agent in the device
            y : y pixel of agent in the device
    """
    for j in range(len(trail_data)):
        x, y = xy_to_pixels(trail_data[j][0], trail_data[j][1], key_dict)
        if vision:
            img = cv2.circle(img, (int(x), int(y)), radius - 10, rgb, -1)
        else:
            img = cv2.circle(img, (int(x), int(y)), radius, rgb, -1)

    return img


def draw_agent_trail(img, trail_data, rgb, vision):
    """ draw agent trail on the device with given color.

        Args:
            img : cv2 read image of device.
            trail_data : data of trail data of the agent
            rgb : (r,g,b) tuple of rgb color

        Returns:
            img : updated image with agent trail drawn.
    """
    for j in range(len(trail_data)):
        if j > 0:
            if vision:
                cv2.line(img, trail_data[j], trail_data[j - 1], rgb, 5)
            else:
                cv2.line(img, trail_data[j], trail_data[j - 1], rgb, 12)
    return img


def show_keypress(img, action_x, action_y, key_dict):
    """ highlights the pressed key.

        Args:
            img : cv2 read image of device.
            action_x : col of the action.
            action_y : row of the action.

        Returns:
            keypress_img : image with agent drawn
            x : x pixel of agent in the device
            y : y pixel of agent in the device
    """
    x, y = xy_to_pixels(action_x, action_y, key_dict)
    x1 = 0;
    x2 = 0

    # keypress for backspace
    if action_x == 2 and action_y == 9:
        x1 = x - (key_width / 2);
        x2 = x + (key_width / 2) + (1 * key_width)
    elif action_x == 2 and action_y == 10:
        x1 = x - (key_width / 2) - (1 * key_width);
        x2 = x + (key_width / 2)

    # keypress for space
    elif action_x == 3 and action_y == 3:
        x1 = x - (key_width / 2);
        x2 = x + (key_width / 2) + (4 * key_width)
    elif action_x == 3 and action_y == 4:
        x1 = x - (key_width / 2) - (1 * key_width);
        x2 = x + (key_width / 2) + (3 * key_width)
    elif action_x == 3 and action_y == 5:
        x1 = x - (key_width / 2) - (2 * key_width);
        x2 = x + (key_width / 2) + (2 * key_width)
    elif action_x == 3 and action_y == 6:
        x1 = x - (key_width / 2) - (3 * key_width);
        x2 = x + (key_width / 2) + (1 * key_width)
    elif action_x == 3 and action_y == 7:
        x1 = x - (key_width / 2) - (4 * key_width);
        x2 = x + (key_width / 2)

    # keypress for enter
    elif action_x == 3 and action_y == 8:
        x1 = x - (key_width / 2);
        x2 = x + (key_width / 2) + (2 * key_width)
    elif action_x == 3 and action_y == 9:
        x1 = x - (key_width / 2) - (1 * key_width);
        x2 = x + (key_width / 2) + (1 * key_width)
    elif action_x == 3 and action_y == 10:
        x1 = x - (key_width / 2) - (2 * key_width);
        x2 = x + (key_width / 2)

    # other keypresses
    else:
        x1 = x - (key_width / 2);
        x2 = x + (key_width / 2)

    keypress_img = cv2.rectangle(img, (int(x1), int(y - key_height / 2)), (int(x2), int(y + key_height / 2)),
                                 (80, 80, 80), -1)

    return keypress_img


def update_text_area(text, action_x, action_y):
    """ updates the text area region.

        Args:
            text : current typed text.
            action_x : col of the action.
            action_y : row of the action.

        Returns:
            text : new text after taking action
    """

    key = xy_to_key(int(action_x), int(action_y))
    if key == '<':
        text = text[:-1]
    elif key == '>':
        text = text
    else:
        text += key
    return text


def add_details(img, screen_img, text, has_vision, has_finger, model_time):
    """ add details to the screen image.

        Args:
            img : current cv2 read image.
            screen_img : original cv2 read device image.
            text : current text.
            has_vision : bool
            has_finger : bool
            model_time : current model time

        Returns:
            img : updated image
    """
    img = cv2.addWeighted(img, alpha, screen_img, 1 - alpha, 0)
    img_pil = Image.fromarray(img)
    draw = ImageDraw.Draw(img_pil)
    draw.text((30, 80), text, font=font, fill=(0, 0, 0, 0))
    img = np.array(img_pil)
    # cv2.putText(img, text, (520, 485), cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(img, "Trial time = " + str(model_time) + "ms", (30, 250), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3,
                cv2.LINE_AA)
    if has_vision:
        cv2.putText(img, 'Eye', (30, 440), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.circle(img, (440, 420), 30, eye_rgb, -1)
    if has_finger:
        cv2.putText(img, 'Finger', (30, 560), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.circle(img, (440, 540), 40, finger_rgb, -1)

    return img


def save_video(screen_img, screen_arr, output_file):
    """ Saves the image frames as a video

        Args:
            screen_img : original cv2 read device image.
            screen_arr : screen frames.
            output_file : name of the output file
    """
    size = (int(screen_img.shape[1]), int(screen_img.shape[0]))
    fourcc = cv2.VideoWriter_fourcc(*'MP4V')
    out = cv2.VideoWriter(output_file, fourcc, fps, size)
    for i in range(len(screen_arr)):
        out.write(screen_arr[i])
    out.release()


def get_screenshot_key(screenshot_name):
    df = load_dataframe()
    screenshot_df = df[df['screenshot_name'] == screenshot_name]
    key_dict = dict()
    index = screenshot_df.loc[screenshot_df['screenshot_name'] == screenshot_name].index[0]
    for column in screenshot_df.columns:
        key_dict[column] = screenshot_df.at[index, column]
    key_dict['-'] = key_dict['shift']
    return key_dict


def visualise_agent(has_vision, has_finger, vision_file, finger_file, output_file, kbd=None):
    screen_arr = []
    eye_trail = []
    finger_trail = []
    eye_point_trail = []
    finger_point_trail = []
    text = ""
    data_size = 0
    assert kbd in keyboard_name.keys() or kbd == 'chi', "Keyboard not supported"
    if kbd in keyboard_name.keys():
        print("visualising {}".format(keyboard_name[kbd]))
        img_path = get_imgpath(keyboard_name[kbd])
        screen_img = cv2.imread(img_path)

        screenshot_name = img_path.split('/')[-1].split('.')[0]
        key_dict = get_screenshot_key(screenshot_name)
    else:
        print("visualising original CHI keyboard")
        screen_img = cv2.imread("./data/images/chikbd.png")
        key_dict = CHI21_KEYS
        key_dict['-'] = key_dict['shift']

    if has_vision:
        print("has vision")
        eye_data = read_data_from_csv(vision_file)
        eye_data = interp_test_data(eye_data)
        if data_size == 0:  data_size = len(eye_data)

    if has_finger:
        print("has finger")
        finger_data = read_data_from_csv(finger_file)
        finger_data = interp_cubic_test_data(finger_data)
        if data_size == 0:  data_size = len(finger_data)

    for i in range(data_size):
        img = screen_img.copy()
        if has_finger:
            # drawing keypress if action is present
            if not finger_data[i][3] == "":
                # img = show_keypress(img, int(finger_data[i][3]), int(finger_data[i][4]))
                text = update_text_area(text, finger_data[i][3], finger_data[i][4])
                finger_point_trail.append((finger_data[i][1], finger_data[i][2]))

            img = draw_agent_points(img, finger_point_trail, finger_rgb, False, key_dict)
            img, fingerloc_x, fingerloc_y = draw_agent(img, finger_data[i][1], finger_data[i][2], finger_rgb, key_dict)

            finger_trail.append((fingerloc_x, fingerloc_y))
            # if len(finger_trail) > 10: finger_trail.pop(0)  # restriciting trail size to 10
            img = draw_agent_trail(img, finger_trail, finger_rgb, False)
            img = add_details(img, screen_img, text, has_vision, has_finger, finger_data[i][0])

        if has_vision:
            # drawing keypress if action is present
            if not eye_data[i][3] == "" and not has_finger:
                # img = show_keypress(img, int(eye_data[i][3]), int(eye_data[i][4]))
                text = update_text_area(text, eye_data[i][3], eye_data[i][4])

            if not eye_data[i][3] == "":
                eye_point_trail.append((eye_data[i][1], eye_data[i][2]))

            img = draw_agent_points(img, eye_point_trail, eye_rgb, True, key_dict)
            img, eyeloc_x, eyeloc_y = draw_agent(img, eye_data[i][1], eye_data[i][2], eye_rgb, key_dict)
            eye_trail.append((eyeloc_x, eyeloc_y))
            # if len(eye_trail) > 10: eye_trail.pop(0)  # restriciting trail size to 10
            img = draw_agent_trail(img, eye_trail, eye_rgb, True)
            img = add_details(img, screen_img, text, has_vision, has_finger, eye_data[i][0])

        screen_arr.append(img)

    save_video(screen_img, screen_arr, output_file)

# def visualise_vision_agent(test_data_file, output_file):

#     data = read_data_from_csv(test_data_file)
#     data = interp_data(data)

#     screen_img = cv2.imread(device_img)

#     screen_arr = []
#     eye_trail = []
#     text = ""
#     alpha = 0.7  # Transparency factor
#     for i in range(len(data)):
#         img = screen_img.copy()
#         if not data[i][3] == "":
#             img = show_keypress(img, int(data[i][3]), int(data[i][4]))
#             text = change_text(text, data[i][3], data[i][4])

#         img, eyeloc_x, eyeloc_y = show_eyelocation(img, data[i][1], data[i][2])
#         eye_trail.append((int(eyeloc_x), int(eyeloc_y)))
#         if len(eye_trail) > 10 :
#             eye_trail.pop(0)

#         for j in range(len(eye_trail)):
#             if j > 0 :
#                 cv2.line(img, eye_trail[j],eye_trail[j-1], (0,255,0), 5)


#         img = cv2.addWeighted(img, alpha, screen_img, 1 - alpha, 0)

#         cv2.putText(img, text,(520,485), cv2.FONT_HERSHEY_SIMPLEX,3,(0,0,0),3,cv2.LINE_AA)
#         cv2.putText(img, "Trial time = " + str(int(data[i][0])) + "ms",(500,150),cv2.FONT_HERSHEY_SIMPLEX,2,(0,0,0),3,cv2.LINE_AA)
#         cv2.putText(img,'Eye',(30,520), cv2.FONT_HERSHEY_SIMPLEX,2,(0,0,0),3,cv2.LINE_AA)
#         cv2.circle(img,(440,500),40,(0,255,0),-1)

#         screen_arr.append(img)

#     size = (int(screen_img.shape[1]),int(screen_img.shape[0]))
#     fourcc = cv2.VideoWriter_fourcc(*'MP4V')
#     out = cv2.VideoWriter(output_file,fourcc, 50.0, size)
#     for i in range(len(screen_arr)):
#         out.write(screen_arr[i])
#     out.release()

# def visualise_finger_agent(test_data_file, output_file):

#     data = read_data_from_csv(test_data_file)
#     data = interp_data(data)

#     screen_img = cv2.imread(device_img)

#     screen_arr = []
#     finger_trail = []
#     text = ""
#     alpha = 0.7  # Transparency factor
#     for i in range(len(data)):
#         img = screen_img.copy()
#         if not data[i][3] == "":
#             img = show_keypress(img, int(data[i][3]), int(data[i][4]))
#             text = change_text(text, data[i][3], data[i][4])

#         img, fingerloc_x, fingerloc_y = show_fingerlocation(img, data[i][1], data[i][2])
#         finger_trail.append((int(fingerloc_x), int(fingerloc_y)))
#         if len(finger_trail) > 10 :
#             finger_trail.pop(0)

#         for j in range(len(finger_trail)):
#             if j > 0 :
#                 cv2.line(img, finger_trail[j],finger_trail[j-1], (255,0,0), 5)


#         img = cv2.addWeighted(img, alpha, screen_img, 1 - alpha, 0)

#         cv2.putText(img, text,(520,485), cv2.FONT_HERSHEY_SIMPLEX,2,(0,0,0),3,cv2.LINE_AA)
#         cv2.putText(img, "Trial time = " + str(int(data[i][0])) + "ms",(500,150),cv2.FONT_HERSHEY_SIMPLEX,2,(0,0,0),3,cv2.LINE_AA)
#         cv2.putText(img,'Finger',(30,520), cv2.FONT_HERSHEY_SIMPLEX,2,(0,0,0),3,cv2.LINE_AA)
#         cv2.circle(img,(440,500),40,(255,0,0),-1)

#         screen_arr.append(img)

#     size = (int(screen_img.shape[1]),int(screen_img.shape[0]))
#     fourcc = cv2.VideoWriter_fourcc(*'MP4V')
#     out = cv2.VideoWriter("./output/output_finger.mp4",fourcc, 50.0, size)
#     for i in range(len(screen_arr)):
#         out.write(screen_arr[i])
#     out.release()