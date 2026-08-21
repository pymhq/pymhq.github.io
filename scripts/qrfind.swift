// Report machine-readable codes found in images. Used by check_photo_masks.py.
//
// One line per symbol found:
//   <path>\t<symbology>\t<x> <y> <w> <h>\tpayload_bytes=<n>
// and one line per file with none:
//   <path>\tclean
//
// The box is normalised to the image with a top-left origin, which is the space
// scripts/build_photo_derivatives.py masks in. Vision reports a bottom-left
// origin, so y is flipped here.
//
// Payload contents are deliberately never printed. The whole point of the mask
// is that a badge's registration data stops being readable, and echoing it into
// a build log would defeat that.
//
// Build: swiftc -O -o <out> scripts/qrfind.swift

import Foundation
import Vision

let paths = Array(CommandLine.arguments.dropFirst())
guard !paths.isEmpty else {
    FileHandle.standardError.write("usage: qrfind <image>...\n".data(using: .utf8)!)
    exit(2)
}

var failed = false

for path in paths {
    guard let src = CGImageSourceCreateWithURL(URL(fileURLWithPath: path) as CFURL, nil),
          let img = CGImageSourceCreateImageAtIndex(src, 0, nil) else {
        print("\(path)\tunreadable")
        failed = true
        continue
    }

    let request = VNDetectBarcodesRequest()
    if #available(macOS 11.0, *) {
        request.symbologies = [.qr, .aztec, .dataMatrix, .pdf417, .microQR]
    }

    do {
        try VNImageRequestHandler(cgImage: img, options: [:]).perform([request])
    } catch {
        print("\(path)\terror\t\(error)")
        failed = true
        continue
    }

    let results = request.results ?? []
    if results.isEmpty {
        print("\(path)\tclean")
        continue
    }
    for obs in results {
        let b = obs.boundingBox
        let y = 1.0 - b.origin.y - b.size.height
        let box = String(format: "%.5f %.5f %.5f %.5f",
                         b.origin.x, y, b.size.width, b.size.height)
        let bytes = obs.payloadStringValue?.utf8.count ?? 0
        print("\(path)\t\(obs.symbology.rawValue)\t\(box)\tpayload_bytes=\(bytes)")
    }
}

exit(failed ? 1 : 0)
