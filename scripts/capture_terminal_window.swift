// capture_terminal_window.swift — record ONE Terminal.app window via
// ScreenCaptureKit (window pixels only: occluding apps never bleed in).
// Usage: ./capture_terminal_window <window-title-substring> <out.mov>
// Build: swiftc -O -o capture_terminal_window capture_terminal_window.swift \
//          -framework ScreenCaptureKit -framework AVFoundation \
//          -framework CoreMedia -framework CoreVideo -framework AppKit
import ScreenCaptureKit
import AVFoundation
import Foundation
import AppKit

// AppKit must be initialized before SCShareableContent on some macOS
// versions (CGS_REQUIRE_INIT assertion otherwise).
let _app = NSApplication.shared
_app.setActivationPolicy(.accessory)

let args = CommandLine.arguments
guard args.count >= 3 else {
    FileHandle.standardError.write("usage: capture_terminal_window <title-substring> <out.mov>\n".data(using: .utf8)!)
    exit(2)
}
let needle = args[1]
let outURL = URL(fileURLWithPath: args[2])

class Recorder: NSObject, SCStreamOutput {
    var writer: AVAssetWriter!
    var input: AVAssetWriterInput!
    var adaptor: AVAssetWriterInputPixelBufferAdaptor!
    var started = false
    var frames = 0
    var failed = false

    func stream(_ s: SCStream, didOutputSampleBuffer sb: CMSampleBuffer, of type: SCStreamOutputType) {
        guard type == .screen, sb.isValid else { return }
        guard let pb = CMSampleBufferGetImageBuffer(sb) else { return }
        let pts = sb.presentationTimeStamp
        if !started {
            started = true
            writer.startSession(atSourceTime: pts)
        }
        guard input.isReadyForMoreMediaData else { return }
        if adaptor.append(pb, withPresentationTime: pts) {
            frames += 1
        } else {
            failed = true
        }
    }
}

let sem = DispatchSemaphore(value: 0)
Task {
    do {
        let content = try await SCShareableContent.excludingDesktopWindows(false, onScreenWindowsOnly: false)
        guard let win = content.windows.first(where: {
            ($0.title ?? "").contains(needle) &&
            $0.owningApplication?.bundleIdentifier == "com.apple.Terminal"
        }) else {
            FileHandle.standardError.write("no matching Terminal window for '\(needle)'\n".data(using: .utf8)!)
            exit(3)
        }
        print("capturing window id=\(win.windowID) '\(win.title ?? "")' \(Int(win.frame.width*2))x\(Int(win.frame.height*2))")

        let filter = SCContentFilter(desktopIndependentWindow: win)
        let cfg = SCStreamConfiguration()
        cfg.width = Int(win.frame.width) * 2
        cfg.height = Int(win.frame.height) * 2
        cfg.pixelFormat = kCVPixelFormatType_32BGRA
        cfg.showsCursor = true
        cfg.minimumFrameInterval = CMTime(value: 1, timescale: 30)

        let rec = Recorder()
        let writer = try AVAssetWriter(url: outURL, fileType: .mov)
        let settings: [String: Any] = [
            AVVideoCodecKey: AVVideoCodecType.h264,
            AVVideoWidthKey: cfg.width,
            AVVideoHeightKey: cfg.height,
            AVVideoCompressionPropertiesKey: [
                AVVideoAverageBitRateKey: 8_000_000
            ]
        ]
        let input = AVAssetWriterInput(mediaType: .video, outputSettings: settings)
        input.expectsMediaDataInRealTime = true
        let adaptor = AVAssetWriterInputPixelBufferAdaptor(
            assetWriterInput: input,
            sourcePixelBufferAttributes: [
                kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA,
                kCVPixelBufferWidthKey as String: cfg.width,
                kCVPixelBufferHeightKey as String: cfg.height
            ])
        writer.add(input)
        rec.writer = writer
        rec.input = input
        rec.adaptor = adaptor
        writer.startWriting()

        let stream = SCStream(filter: filter, configuration: cfg, delegate: nil)
        try stream.addStreamOutput(rec, type: .screen, sampleHandlerQueue: .global())
        try await stream.startCapture()

        // Record until killed (SIGINT/SIGTERM) — the caller drives duration.
        let done = DispatchSemaphore(value: 0)
        signal(SIGINT, SIG_IGN); signal(SIGTERM, SIG_IGN)
        DispatchQueue.global().async {
            let src = DispatchSource.makeSignalSource(signal: SIGTERM, queue: .global())
            src.setEventHandler { done.signal() }
            src.resume()
            let src2 = DispatchSource.makeSignalSource(signal: SIGINT, queue: .global())
            src2.setEventHandler { done.signal() }
            src2.resume()
            RunLoop.current.run()
        }
        done.wait()
        try await stream.stopCapture()
        input.markAsFinished()
        await withCheckedContinuation { (c: CheckedContinuation<Void, Never>) in
            writer.finishWriting { c.resume() }
        }
        print("done. frames=\(rec.frames) failed=\(rec.failed) status=\(writer.status.rawValue) err=\(String(describing: writer.error)) -> \(outURL.path)")
        exit(0)
    } catch {
        FileHandle.standardError.write("error: \(error)\n".data(using: .utf8)!)
        exit(1)
    }
}
sem.wait()
