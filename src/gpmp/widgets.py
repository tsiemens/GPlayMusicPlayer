"""Custom widget definitions"""

from PySide2 import QtCore, QtWidgets
from PySide2.QtWidgets import QStyle

class MediaSlider(QtWidgets.QSlider):
   # Override
   def mousePressEvent(self, event):
      """Overrides the default mouse event such that if the user clicks
      on an area of the slider which is not the handle, the value will immediately
      jump to that position.
      Emits on sliderReleased after the value is updated.
      """
      if event.button() == QtCore.Qt.LeftButton and not self.pos_inside_handle(event.pos()):
         event.accept()
         val = self.pixel_pos_to_range_value(event.pos())
         self.setValue(val)
         self.sliderReleased.emit()
      else:
         super().mousePressEvent(event)

   def pos_inside_handle(self, pos: QtCore.QPoint):
      opt = QtWidgets.QStyleOptionSlider()
      # Populate opt with the widget's style
      self.initStyleOption(opt)
      handle = self.style().subControlRect(QStyle.CC_Slider, opt,
                                           QStyle.SC_SliderHandle, self)

      topleft = handle.topLeft()
      bottomright = handle.bottomRight()
      return (pos.x() >= topleft.x() and pos.x() <= bottomright.x() and
              pos.y() >= topleft.y() and pos.y() <= bottomright.y())

   def pixel_pos_to_range_value(self, pos: QtCore.QPoint):
      opt = QtWidgets.QStyleOptionSlider()
      # Populate opt with the widget's style
      self.initStyleOption(opt)
      groove = self.style().subControlRect(QStyle.CC_Slider, opt,
                                           QStyle.SC_SliderGroove, self)

      if self.orientation() == QtCore.Qt.Horizontal:
         #  sliderLength = handle.width()
         slider_min = groove.x()
         slider_max = groove.right()
      else:
         #  sliderLength = handle.height()
         slider_min = groove.y()
         slider_max = groove.bottom()

      new_pos_scalar = pos.x() if self.orientation() == QtCore.Qt.Horizontal else pos.y()
      return QStyle.sliderValueFromPosition(self.minimum(), # min
                                            self.maximum(), # max
                                            new_pos_scalar, # pos (int)
                                            slider_max - slider_min, # span (int)
                                            opt.upsideDown # upside down (bool)
                                            )
