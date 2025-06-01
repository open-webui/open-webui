export const getProductImages = (dir: string = '/assets/images/'): string[] => {
  const maxImages = 283;
  const imageUrls = [];
  for (let i = 1; i <= maxImages; i++) {
    const imageUrl = `${dir}${i}.jpeg`;
    imageUrls.push(imageUrl);
  }
  for (let i = imageUrls.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [imageUrls[i], imageUrls[j]] = [imageUrls[j], imageUrls[i]];
  }
  return imageUrls;
};