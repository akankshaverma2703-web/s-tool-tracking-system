import qrcode
qr = qrcode.make("EMP001")
qr.save("qr_EMP001.png")
print("Saved!")
