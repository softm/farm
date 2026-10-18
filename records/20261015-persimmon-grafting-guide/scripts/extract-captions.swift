/* SOFTM-GRAFT-OCR START: 원본 이미지 하단 자막을 Apple Vision으로 일괄 추출 (2026-10-18) */
import AppKit
import Foundation
import Vision

struct GalleryItem: Decodable {
    let sequence: String
    let file: String
}

struct RecognizedLine {
    let text: String
    let x: CGFloat
    let y: CGFloat
    let width: CGFloat
    let height: CGFloat
    let confidence: VNConfidence
}

enum CaptionExtractorError: LocalizedError {
    case invalidArguments
    case invalidGalleryData
    case unreadableImage(String)

    var errorDescription: String? {
        switch self {
        case .invalidArguments:
            return "사용법: swift scripts/extract-captions.swift <프로젝트 경로>"
        case .invalidGalleryData:
            return "gallery-data.js에서 이미지 목록을 읽지 못했습니다."
        case let .unreadableImage(path):
            return "이미지를 읽지 못했습니다: \(path)"
        }
    }
}

func loadGalleryItems(from projectURL: URL) throws -> [GalleryItem] {
    let dataURL = projectURL.appendingPathComponent("gallery-data.js")
    let source = try String(contentsOf: dataURL, encoding: .utf8)

    guard
        let arrayStart = source.firstIndex(of: "["),
        let arrayEnd = source.range(of: "];", options: .backwards)?.lowerBound
    else {
        throw CaptionExtractorError.invalidGalleryData
    }

    let jsonText = String(source[arrayStart...arrayEnd])
    guard let jsonData = jsonText.data(using: .utf8) else {
        throw CaptionExtractorError.invalidGalleryData
    }
    return try JSONDecoder().decode([GalleryItem].self, from: jsonData)
}

func recognizeLines(in imageURL: URL) throws -> [RecognizedLine] {
    guard let image = NSImage(contentsOf: imageURL) else {
        throw CaptionExtractorError.unreadableImage(imageURL.path)
    }

    var imageRect = NSRect(origin: .zero, size: image.size)
    guard let cgImage = image.cgImage(forProposedRect: &imageRect, context: nil, hints: nil) else {
        throw CaptionExtractorError.unreadableImage(imageURL.path)
    }

    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.recognitionLanguages = ["ko-KR", "en-US"]
    request.usesLanguageCorrection = true
    request.minimumTextHeight = 0.012

    let handler = VNImageRequestHandler(cgImage: cgImage)
    try handler.perform([request])

    return (request.results ?? []).compactMap { observation in
        guard let candidate = observation.topCandidates(1).first else { return nil }
        return RecognizedLine(
            text: candidate.string,
            x: observation.boundingBox.origin.x,
            y: observation.boundingBox.origin.y,
            width: observation.boundingBox.width,
            height: observation.boundingBox.height,
            confidence: candidate.confidence
        )
    }
}

func normalizedCaption(from lines: [RecognizedLine]) -> String {
    let subtitleLines = lines
        .filter { line in
            line.y < 0.24
                && line.width > 0.08
                && line.height > 0.015
                && line.confidence >= 0.3
        }
        .sorted { left, right in
            if abs(left.y - right.y) > 0.015 { return left.y > right.y }
            return left.x < right.x
        }
        .map(\.text)

    return subtitleLines
        .joined(separator: " ")
        .replacingOccurrences(of: "\\s+", with: " ", options: .regularExpression)
        .trimmingCharacters(in: .whitespacesAndNewlines)
}

do {
    guard CommandLine.arguments.count == 2 else {
        throw CaptionExtractorError.invalidArguments
    }

    let projectURL = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
    let items = try loadGalleryItems(from: projectURL)

    print("sequence\tfile\tocr_caption")
    for item in items {
        let imageURL = projectURL.appendingPathComponent(item.file)
        let lines = try recognizeLines(in: imageURL)
        let caption = normalizedCaption(from: lines)
            .replacingOccurrences(of: "\t", with: " ")
            .replacingOccurrences(of: "\n", with: " ")
        let fields = caption.isEmpty
            ? [item.sequence, item.file]
            : [item.sequence, item.file, caption]
        print(fields.joined(separator: "\t"))
    }
} catch {
    FileHandle.standardError.write(Data("오류: \(error.localizedDescription)\n".utf8))
    exit(1)
}
/* SOFTM-GRAFT-OCR END: 원본 이미지 하단 자막을 Apple Vision으로 일괄 추출 (2026-10-18) */
