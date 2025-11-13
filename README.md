# NiimCtl

A minimal command line tool for printing labels on a NiimBot B1.  This is not officially supported maintained or related to NiimBot.

I wrote this tool to let me quickly and easily print labels designed in Inkscape on a B1 printer from Linux.

The code is built upon what I learned by reading [NiimPrintX](https://github.com/labbots/NiimPrintX) which wouldn't work with my B1.  The documentation at [NIIMBOT Community Wiki](https://printers.niim.blue/interfacing/proto/) and some serial dumps from printing with the [niim.blue](https://niim.blue) web app.

# Installing

It doesn't need installing, it's just a single Python script, copy it download it, clone it whatever.

The only dependencies other than core Python libs are:

* pyserial (`sudo apt install python3-serial`)
* PIL (`sudo apt install python3-pil`)

No special versions of Python or these dependencies are required, I built it on Ubuntu 24.04 but I've not used any new or cutting edge features.

# Using

There's an example label in the examples folder.  This is just an Inkscape SVG I created and set the page size to 50x30mm.  To print it you need to first invoke Inkscape from the command line to export an SVG:

    inkscape --export-width=384 --export-type=png --export-filename=examples/label.png examples/label.svg

There's also an example for the 10x20mm labels which come in groups of 4 so you need to print 4 labels at once effectively a 40x20 label.  The 40mm label sits in the middle of the 50mm printer, the example uses guides to split the space up into 4 areas for each of the labels.  Export as a single PNG:

    inkscape --export-width=384 --export-type=png --export-filename=examples/label.png examples/label_10x20x4.svg

Then send that to the printer:

    python3 niimctl.py -p /dev/ttyACM0 -i examples/label.png
