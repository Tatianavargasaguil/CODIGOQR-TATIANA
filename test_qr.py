import qrcode
from io import BytesIO
import base64

codigo_qr = "veh_" + 'abcd1234'
qr = qrcode.QRCode(
    version=1,
    error_correction=qrcode.constants.ERROR_CORRECT_L,
    box_size=10,
    border=4,
)
qr.add_data(codigo_qr)
qr.make(fit=True)
img = qr.make_image(fill_color="black", back_color="white")
print('image type', type(img))
buffered = BytesIO()
img.save(buffered, format="PNG")
print('saved image size', len(buffered.getvalue()))
