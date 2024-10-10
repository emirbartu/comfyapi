from PIL import Image, ImageTk
import tkinter as tk

def show_example_image():
    # Tkinter penceresi oluşturma
    root = tk.Tk()
    root.title("Display Image")

    # example.png dosyasını aç
    image = Image.open("angry.png")

    # PIL Image'ı Tkinter ile kullanılabilir hale getir
    tk_image = ImageTk.PhotoImage(image)

    # Görüntüyü göstermek için bir etiket widget'ı oluştur
    label = tk.Label(root, image=tk_image)
    label.pack()

    # Tkinter event loop başlat
    root.mainloop()

# Örnek görüntüyü göster
show_example_image()
