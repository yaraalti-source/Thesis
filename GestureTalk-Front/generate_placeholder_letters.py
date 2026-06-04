"""
Generate placeholder ASL letter images (A-Z)
Run this script to quickly create letter images for testing.
Later, replace with real ASL sign images.
"""

from PIL import Image, ImageDraw, ImageFont
import os

def generate_letter_images():
    # Create output directory
    output_dir = 'assets/signs/letters'
    os.makedirs(output_dir, exist_ok=True)
    
    print("Generating ASL letter placeholder images...")
    print(f"Output directory: {output_dir}\n")
    
    # Generate placeholder images for each letter
    for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
        # Create white background
        img = Image.new('RGB', (400, 400), color='white')
        draw = ImageDraw.Draw(img)
        
        # Try to use a nice font, fallback to default
        try:
            # Try different font paths for cross-platform compatibility
            font_paths = [
                "arial.ttf",  # Windows
                "/System/Library/Fonts/Helvetica.ttc",  # macOS
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
            ]
            font = None
            for font_path in font_paths:
                try:
                    font = ImageFont.truetype(font_path, 180)
                    break
                except:
                    continue
            
            if font is None:
                raise Exception("No font found")
                
        except Exception as e:
            print(f"Warning: Could not load truetype font, using default. Error: {e}")
            font = ImageFont.load_default()
        
        # Draw the letter in the center
        text = letter
        
        # Get text bounding box
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Center the text
        x = (400 - text_width) // 2
        y = (400 - text_height) // 2 - 30
        
        # Draw letter in blue
        draw.text((x, y), text, fill='#4A90E2', font=font)
        
        # Add "ASL" label at bottom
        try:
            small_font = ImageFont.truetype(font_paths[0] if font else "arial.ttf", 30)
        except:
            small_font = font
        
        label_text = f"ASL Letter {letter}"
        label_bbox = draw.textbbox((0, 0), label_text, font=small_font)
        label_width = label_bbox[2] - label_bbox[0]
        label_x = (400 - label_width) // 2
        
        draw.text((label_x, 340), label_text, fill='#666666', font=small_font)
        
        # Draw a subtle border
        draw.rectangle([(10, 10), (390, 390)], outline='#E0E0E0', width=2)
        
        # Save image
        output_path = os.path.join(output_dir, f'{letter}.png')
        img.save(output_path)
        print(f"✓ Generated {letter}.png")
    
    print(f"\n{'='*50}")
    print("✓ All 26 letter placeholders generated successfully!")
    print(f"{'='*50}")
    print(f"\nImages saved to: {output_dir}")
    print("\nNext steps:")
    print("1. Run 'flutter pub get' in your Flutter project")
    print("2. Restart the app (not hot reload)")
    print("3. Test Voice-to-Sign feature")
    print("\nNote: Replace these placeholders with real ASL images later.")

if __name__ == "__main__":
    try:
        generate_letter_images()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("\nMake sure you have Pillow installed:")
        print("  pip install pillow")









