# Store listing

- **Story:** robots have breached your moon base through its main airlock; push them back out.
- **Icon:** `store/icon.png`, three drones in formation (24x24, #F4F4F4 on transparent, 2x2 pixel blocks; drawn by `store/make_icon.py`)
- **Name** (19/20): G2TD: Tower Defense (G2TD: G-squared Tower Defense)
- **Tagline** (20/50): Sci-fi Tower Defense
- **Description** (under 2000): `store/description.txt`
- **Tags:** Games, Strategy, Tower Defense, Sci-Fi, Pixel Art

Set name, tagline, description and icon (unpublished apps only):

```bash
npx evenhub update --name "G2TD: Tower Defense" --tagline "Sci-fi Tower Defense" --description-file store/description.txt --icon store/icon.png
```

Tags aren't an option of `evenhub update`; set them on the hub. The package id stays `com.elsethenif.g2td`.
