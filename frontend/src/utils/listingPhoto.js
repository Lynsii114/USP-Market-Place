export const LISTING_PHOTO_ACCEPT = ".jpg,.jpeg,.jfif,.png,.webp,.avif,image/jpeg,image/png,image/webp,image/avif";
const MAX_INPUT_BYTES = 5 * 1024 * 1024;
const MAX_SAVED_BYTES = 1024 * 1024;
const IMAGE_TYPES = new Set(["image/jpeg", "image/png", "image/webp", "image/avif"]);
const IMAGE_EXTENSION = /\.(jpe?g|jfif|png|webp|avif)$/i;

export async function prepareListingPhoto(file) {
  const recognizedType = IMAGE_TYPES.has(file.type);
  const missingType = !file.type || file.type === "application/octet-stream";
  if (!recognizedType && !(missingType && IMAGE_EXTENSION.test(file.name))) {
    throw new Error("Choose a JPEG, PNG, WebP or AVIF image.");
  }
  if (file.size === 0) throw new Error("The selected image is empty. Choose another photo.");
  if (file.size > MAX_INPUT_BYTES) throw new Error("Choose an image no larger than 5 MB.");

  const url = URL.createObjectURL(file);
  try {
    const image = await new Promise((resolve, reject) => {
      const candidate = new Image();
      candidate.onload = () => resolve(candidate);
      candidate.onerror = () => reject(new Error("This image could not be opened. Try another photo or export it as JPEG or PNG."));
      candidate.src = url;
    });
    const canvas = document.createElement("canvas");
    const scale = Math.min(1, 1600 / Math.max(image.naturalWidth, image.naturalHeight));
    canvas.width = Math.max(1, Math.round(image.naturalWidth * scale));
    canvas.height = Math.max(1, Math.round(image.naturalHeight * scale));
    canvas.getContext("2d").drawImage(image, 0, 0, canvas.width, canvas.height);
    // Keep JSON uploads within the backend request limit. Also normalizes image
    // contents instead of trusting a renamed file's extension.
    for (const quality of [0.85, 0.65, 0.45]) {
      const dataUrl = canvas.toDataURL("image/webp", quality);
      if (dataUrl.length * 0.75 <= MAX_SAVED_BYTES) return dataUrl;
    }
    throw new Error("This photo is too detailed to upload. Resize it or choose a smaller image.");
  } finally {
    URL.revokeObjectURL(url);
  }
}
