import argparse
from pdf2image import convert_from_path
import subprocess
import tempfile
import os

def pdf_to_images(pdf_path, dpi=300):
    print(f"PDFから画像への変換を開始します: {pdf_path}")
    images = convert_from_path(pdf_path, dpi=dpi)
    print(f"PDFから画像への変換が完了しました。ページ数: {len(images)}")
    return images

def image_to_markdown(img_path):
    print(f"  画像からMarkdownへの変換を開始します: {img_path}")
    # YomiToku を CLI 呼び出しする例
    result = subprocess.run(
        ['yomitoku', '--input', img_path, '--format', 'md'],
        capture_output=True, text=True
    )
    print(f"  画像からMarkdownへの変換が完了しました: {img_path}")
    return result.stdout

def main():
    print("処理を開始します...")
    parser = argparse.ArgumentParser()
    parser.add_argument('pdf', help='入力PDFファイル')
    parser.add_argument('md', help='出力Markdownファイル')
    args = parser.parse_args()

    print(f"入力PDF: {args.pdf}")
    print(f"出力Markdown: {args.md}")

    with tempfile.TemporaryDirectory() as workdir:
        print(f"一時ディレクトリを作成しました: {workdir}")
        images = []
        # PDF→画像
        pdf_images = pdf_to_images(args.pdf)
        for i, page in enumerate(pdf_images):
            print(f"  ページ {i+1} を画像として保存中...")
            img_path = os.path.join(workdir, f'page_{i+1}.png')
            page.save(img_path, 'PNG')
            images.append(img_path)
            print(f"  ページ {i+1} を {img_path} に保存しました。")

        # 画像→Markdown
        print("全ページの画像への変換が完了しました。Markdownへの変換を開始します。")
        md_contents = []
        for i, img in enumerate(images):
            print(f"  画像 {i+1}/{len(images)} を処理中: {img}")
            md_contents.append(image_to_markdown(img))
            print(f"  画像 {i+1}/{len(images)} のMarkdown変換が完了しました。")

    # 結合して書き出し
    print(f"Markdownコンテンツを {args.md} に書き出します...")
    with open(args.md, 'w', encoding='utf-8') as f:
        f.write('\\n\\n'.join(md_contents))
    print(f"{args.md} への書き出しが完了しました。")
    print("処理が正常に終了しました。")

if __name__ == '__main__':
    main()
