"""
Copyright 2022 Intel Corporation
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
    http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

LABEL_PERSON          = 1
LABEL_BICYCLE         = 2
LABEL_CAR             = 0
LABEL_MOTORBIKE       = 3
LABEL_AEROPLANE       = 4
LABEL_BUS             = 5
LABEL_TRAIN           = 6
LABEL_TRUCK           = 7
LABEL_BOAT            = 8
LABEL_TRAFFIC_LIGHT   = 9
LABEL_FIRE_HYDRANT    = 10
LABEL_STOP_SIGN       = 11
LABEL_PARKING_METER   = 12
LABEL_BENCH           = 13
LABEL_BIRD            = 14
LABEL_CAT             = 15
LABEL_DOG             = 16
LABEL_HORSE           = 17
LABEL_SHEEP           = 18
LABEL_COW             = 19
LABEL_ELEPHANT        = 20
LABEL_BEAR            = 21
LABEL_ZEBRA           = 22
LABEL_GIRAFFE         = 23
LABEL_BACKPACK        = 24
LABEL_UMBRELLA        = 25
LABEL_HANDBAG         = 26
LABEL_TIE             = 27
LABEL_SUITCASE        = 28
LABEL_FRISBEE         = 29
LABEL_SKIS            = 30
LABEL_SNOWBOARD       = 31
LABEL_SPORTS_BALL     = 32
LABEL_KITE            = 33
LABEL_BASEBALL_BAT    = 34
LABEL_BASEBALL_GLOVE  = 35
LABEL_SKATEBOARD      = 36
LABEL_SURFBOARD       = 37
LABEL_TENNIS_RACKET   = 38
LABEL_BOTTLE          = 39
LABEL_WINE_GLASS      = 40
LABEL_CUP             = 41
LABEL_FORK            = 42
LABEL_KNIFE           = 43
LABEL_SPOON           = 44
LABEL_BOWL            = 45
LABEL_BANANA          = 46
LABEL_APPLE           = 47
LABEL_SANDWICH        = 48
LABEL_ORANGE          = 49
LABEL_BROCCOLI        = 50
LABEL_CARROT          = 51
LABEL_HOT_DOG         = 52
LABEL_PIZZA           = 53
LABEL_DONUT           = 54
LABEL_CAKE            = 55
LABEL_CHAIR           = 56
LABEL_SOFA            = 57
LABEL_POTTEDPLANT     = 58
LABEL_BED             = 59
LABEL_DININGTABLE     = 60
LABEL_TOILET          = 61
LABEL_TVMONITOR       = 62
LABEL_LAPTOP          = 63
LABEL_MOUSE           = 64
LABEL_REMOTE          = 65
LABEL_KEYBOARD        = 66
LABEL_CELL_PHONE      = 67
LABEL_MICROWAVE       = 68
LABEL_OVEN            = 69
LABEL_TOASTER         = 70
LABEL_SINK            = 71
LABEL_REFRIGERATOR    = 72
LABEL_BOOK            = 73
LABEL_CLOCK           = 74
LABEL_VASE            = 75
LABEL_SCISSORS        = 76
LABEL_TEDDY_BEAR      = 77
LABEL_HAIR_DRIER      = 78
LABEL_TOOTHBRUSH      = 79
LABEL_UNKNOWN         = 99

YOLO_LABELS = ("Vehicle", "Person", "Bike", "Motorbike", "Aeroplane", "Bus", "Train", "Truck", 
	"Boat", "Traffic light", "Fire hydrant", "Stop sign", "Parking meter", "Bench", "Bird", "Cat", 
	"Dog", "Horse", "Sheep", "Cow", "Elephant", "Bear", "Zebra", "Giraffe", "Backpack", "Umbrella", 
	"Handbag", "Tie", "Suitcase", "Frisbee", "Skis", "Snowboard", "Sports ball", "Kite", "Baseball bat", 
	"Baseball glove", "Skateboard", "Surfboard", "Tennis racket", "Bottle", "Wine glass", "Cup", "Fork", 
	"Knife", "Spoon", "Bowl", "Banana", "Apple", "Sandwich", "Orange", "Broccoli", "Carrot", "Hot dog", 
	"Pizza", "Donut", "Cake", "Chair", "Sofa", "Pottedplant", "Bed", "Diningtable", "Toilet", "Tvmonitor", 
	"Laptop", "Mouse", "Remote", "Keyboard", "Cell phone", "Microwave", "Oven", "Toaster", "Sink", 
	"Refrigerator", "Book", "Clock", "Vase", "Scissors", "Yeddy bear", "Hair drier", "Toothbrush"
)

COLOR_TRUCK = (255, 0, 255)
COLOR_BUS = (255, 0, 0)
COLOR_BIKE = (0, 255, 0)
COLOR_MOTORBIKE = (0, 0, 255)
COLOR_UNKNOWN = (0, 0, 0)
COLOR_CAR = (0, 255, 255)
COLOR_PERSON = (255, 255, 0)


def get_label_str(label):
    return  YOLO_LABELS[label]

def get_label_color(label):
    switch = {
        LABEL_PERSON: COLOR_PERSON,
        LABEL_CAR: COLOR_CAR,
        LABEL_BUS: COLOR_BUS,
        LABEL_TRUCK: COLOR_TRUCK,
        LABEL_BICYCLE: COLOR_BIKE,
        LABEL_MOTORBIKE: COLOR_MOTORBIKE
    }
    return switch.get(label, COLOR_UNKNOWN);
