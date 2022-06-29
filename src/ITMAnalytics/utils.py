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

class Point(object):
    """
    Point Class
    """
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __add__(self, pt):
        """
        Add two points
        """
        if not isinstance(pt, Point):
            raise TypeError
        return Point(self.x + pt.x, self.y + pt.y)

    def __sub__(self, pt):
        """
        Subtract two points
        """
        if not isinstance(pt, Point):
            raise TypeError
        return Point(self.x - pt.x, self.y - pt.y)

    def __mul__(self, num):
        """
        Multiply two points
        """
        if not isinstance(num, int):
            raise TypeError
        return Point(self.x * num, self.y * num)

    def __rmul__(self, num):
        """
        Same as __mul__
        """
        return self.__mul__(num)

    def __truediv__(self, num):
        """
        Divide two points
        """
        return Point(self.x / num, self.y / num)

    def __rtruediv__(self, num):
        """
        Reverse divide
        """
        return Point(num / self.x, num / self.y)

    def __str__(self):
        return f'Point({self.x}, {self.y})'

class Rect(object):
    """
    Rectangle class
    """
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def start(self):
        """
        Return top-left corner
        """
        return Point(self.x, self.y)

    def end(self):
        """
        Return bottom-right corner
        """
        return Point(self.x+self.width, self.y+self.height)

    def area(self):
        """
        Return area
        """
        return self.width*self.height

    def center(self):
        """
        Return center of Rect
        """
        return Point(self.x + self.width/2, self.y + self.height/2)
    
    def intersect(self, other_rect):
        """
        Return intersect between two Rect
        """
        if not isinstance(other_rect, Rect):
            raise TypeError
        x1 = max(self.x, other_rect.x)
        y1 = max(self.y, other_rect.y)
        x2 = min(self.x+self.width, other_rect.x+other_rect.width)
        y2 = min(self.y+self.height, other_rect.y+other_rect.height)
        if x2 < x1 or y2 < y1:
            return Rect(0, 0, 0, 0)
        return Rect(x1, y1, x2-x1, y2-y1)

    def __str__(self):
        return f'Rect({self.x}, {self.y}, {self.width}, {self.height})'
