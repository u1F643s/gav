import cv2
import os
from PIL import Image, ImageDraw, ImageFont
from concurrent.futures import ThreadPoolExecutor, as_completed
import traceback
import argparse
import json

RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
RESET = "\033[0m"

def main():
    parser = argparse.ArgumentParser(
        description=f'{GREEN}Convert a video to ASCII video{RESET}{BLUE}\nJust in case, gav stands for Generate ASCII Video{RESET}'
    )

    parser.add_argument("-videopath", type=str, default="video.mp4", help="Path to input video")
    parser.add_argument("-output", type=str, default="ascii_frames", help="Folder to save intermediate frames")
    parser.add_argument("-ascii_video", type=str, default="ascii_video.mp4", help="Output ASCII video path")
    parser.add_argument("-fps", type=int, default=20, help="Target FPS for output video")
    parser.add_argument("-width", type=int, default=120, help="ASCII width in characters")
    parser.add_argument("-chars", type=str, default="@%#*+=-:. ", help="ASCII characters from dark to light")
    parser.add_argument("-font_size", type=int, default=12, help="Font size for ASCII images")
    parser.add_argument("-threads", type=int, default=8, help="Max worker threads for conversion")
    parser.add_argument("-font_path", type=str, default="cour.ttf", help="Path to TTF font file")
    parser.add_argument("-json", action="store_true", help="Output frames as JSON instead of video")
    
    args = parser.parse_args()

    doit(
        video_path=args.videopath,
        output_folder=args.output,
        ascii_video_path=args.ascii_video,
        target_fps=args.fps,
        ascii_width=args.width,
        chars=args.chars,
        font_path=args.font_path,
        font_size=args.font_size,
        max_threads=args.threads,
        output_json=args.json
    )
    


def doit(video_path="video.mp4",output_folder="ascii_frames",ascii_video_path = "ascii_video.mp4",target_fps=20,ascii_width=120,chars = "@%#*+=-:. ",font_size = 12, max_threads = 8,font_path="cour.tff", output_json=False):
    os.makedirs(output_folder, exist_ok=True)
    font_size = font_size * 2 # this is because i can't fix the res of the video, sorry
    cap = cv2.VideoCapture(video_path)
    orig_fps = cap.get(cv2.CAP_PROP_FPS)
    frame_skip = max(1, round(orig_fps / target_fps))
    frame_count = 0
    saved_count = 0

    print(BLUE + "Starting frame extraction..."+RESET)

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_count % frame_skip == 0:
            frame_path = f"{output_folder}/frame_{saved_count:04d}.png"
            cv2.imwrite(frame_path, frame)
            print(f"{GREEN}[Frame Extraction] Saved frame {saved_count:04d}{RESET}")
            saved_count += 1
        frame_count += 1

    cap.release()
    print(f"{GREEN}Extracted {saved_count} frames at {target_fps} FPS!{RESET}")

    font = ImageFont.truetype(font_path, font_size)

    def frame_to_ascii_image_safe(img_path, output_path, width=ascii_width):
        try:
            img = Image.open(img_path)
            bbox = font.getbbox("A")
            char_width = bbox[2] - bbox[0]
            char_height = bbox[3] - bbox[1]
            
            wpercent = width / float(img.size[0])
            hsize = int(img.size[1] * (char_width / char_height) * wpercent)
            img = img.resize((width, hsize))
            img = img.convert("L")
            
            pixels = img.getdata()
            ascii_str = "".join([chars[pixel * len(chars) // 256] for pixel in pixels])
            ascii_lines = [ascii_str[i:i+width] for i in range(0, len(ascii_str), width)]
            
            img_out = Image.new("L", (width * char_width * 1, hsize * char_height * 1), color=255) # this is also
            draw = ImageDraw.Draw(img_out)
            for i, line in enumerate(ascii_lines):
                draw.text((0, i * char_height), line, fill=0, font=font)
            
            img_out.save(output_path)
            os.remove(img_path)
            print(f"{GREEN}[ASCII Conversion] Converted {os.path.basename(img_path)}{RESET}")
            
            # Return both path and ASCII lines for flexible output
            ascii_text = "\n".join(ascii_lines)
            return (output_path, ascii_text)
        except Exception:
            print(f"{RED}[Error] Failed to convert {img_path}{RESET}")
            traceback.print_exc()
            return None

    print(f"{BLUE}Starting threaded ASCII conversion...{RESET}")
    ascii_image_paths = []
    ascii_frames_data = {}  # For JSON output
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = []
        for i in range(saved_count):
            img_path = f"{output_folder}/frame_{i:04d}.png"
            ascii_img_path = f"{output_folder}/ascii_{i:04d}.png"
            futures.append(executor.submit(frame_to_ascii_image_safe, img_path, ascii_img_path))
        
        for idx, future in enumerate(as_completed(futures)):
            result = future.result()
            if result:
                img_path, ascii_text = result
                ascii_image_paths.append(img_path)
                ascii_frames_data[f"{idx:04d}"] = ascii_text

    ascii_image_paths.sort()
    print(f"{GREEN}All frames converted and cleaned up!{RESET}")

    if not ascii_image_paths:
        print(f"{YELLOW}No frames to write to output. Exiting.{RESET}")
    elif output_json:
        # Output as JSON
        json_output = {"frames": ascii_frames_data}
        json_path = os.path.splitext(ascii_video_path)[0] + ".json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_output, f, indent=2, ensure_ascii=False)
        print(f"{GREEN}JSON frames saved to {json_path}{RESET}")
        
        # Clean up ASCII images
        for path in ascii_image_paths:
            try:
                os.remove(path)
            except Exception:
                pass
        print(f"{GREEN}Cleaned up ASCII images{RESET}")
    else:
        # Output as video
        frame_example = Image.open(ascii_image_paths[0])
        frame_w, frame_h = frame_example.size
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(ascii_video_path, fourcc, target_fps, (frame_w, frame_h))

        print(f"{BLUE}Starting video writing...{RESET}")
        for i, path in enumerate(ascii_image_paths):
            try:
                img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
                img_color = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
                out.write(img_color)
                print(f"{GREEN}[Video Writing] Wrote frame {i:04d}{RESET}")
                os.remove(path)
            except Exception:
                print(f"{RED}[Error] Failed to write frame {path}{RESET}")
                traceback.print_exc()

        out.release()
        print(f"{GREEN}ASCII video saved as {ascii_video_path} and all frames cleaned up!{RESET}")

if __name__ == "__main__":
    main()
