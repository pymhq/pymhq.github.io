// Count faces per image. Used by check_photo_credits.py to test whether a
// credit is attached to a photograph that can actually contain the people it
// names. Prints "<name>\tfaces=<n>" per file; no image content is otherwise
// inspected and nothing about the faces is recorded.
//
// Build: swiftc -O -o <out> scripts/facecount.swift

import Foundation
import Vision

for path in CommandLine.arguments.dropFirst() {
    guard let src = CGImageSourceCreateWithURL(URL(fileURLWithPath: path) as CFURL, nil),
          let img = CGImageSourceCreateImageAtIndex(src, 0, nil) else {
        print("\((path as NSString).lastPathComponent)\tunreadable")
        continue
    }
    let request = VNDetectFaceRectanglesRequest()
    do {
        try VNImageRequestHandler(cgImage: img, options: [:]).perform([request])
    } catch {
        print("\((path as NSString).lastPathComponent)\terror")
        continue
    }
    print("\((path as NSString).lastPathComponent)\tfaces=\(request.results?.count ?? 0)")
}
