import bookyImage from "../../Booky.jfif";
import clothesImage from "../../Clothes.jfif";
import electronicsImage from "../../Electronics.webp";
import footwearImage from "../../footwares.jfif";
import homeLivingImage from "../../Home and LIving.jpg";
import studyImage from "../assets/categories/study-supplies.jpg";
import sportsImage from "../assets/categories/sports-fitness.jpg";
import careImage from "../assets/categories/personal-care.jpg";
import otherImage from "../assets/categories/other.jpg";

export const categories = [
  { id: "builtin-1", name: "Books", icon: "Book", image: bookyImage },
  { id: "builtin-2", name: "Electronics", icon: "Tech", image: electronicsImage },
  { id: "builtin-3", name: "Clothing", icon: "Wear", image: clothesImage },
  { id: "builtin-4", name: "Furniture", icon: "Home", image: homeLivingImage },
  { id: "builtin-5", name: "Footwear", icon: "Shoes", image: footwearImage },
  { id: "builtin-6", name: "Study Supplies", icon: "Study", image: studyImage },
  { id: "builtin-7", name: "Sports & Fitness", icon: "Sport", image: sportsImage },
  { id: "builtin-8", name: "Personal Care", icon: "Care", image: careImage, imagePosition: "center 65%" },
  { id: "builtin-9", name: "Other", icon: "More", image: otherImage },
];
