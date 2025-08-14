# import cv2
#
# # 打开两个摄像头
# cap0 = cv2.VideoCapture(1)
#
# while True:
#     ret0, frame0 = cap0.read()
#
#     if ret0:
#         cv2.imshow("Camera 0", frame0)
#
#     # 按 q 键退出
#     if cv2.waitKey(1) & 0xFF == ord('q'):
#         break
#
# cap0.release()
# cv2.destroyAllWindows()