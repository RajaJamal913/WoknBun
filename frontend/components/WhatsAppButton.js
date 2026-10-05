import { FaWhatsapp } from "react-icons/fa";

const NUMBER = "923035313933";
const MESSAGE = "Hi Wok & Bun, I'd like to place an order.";

export const WHATSAPP_URL = `https://wa.me/${NUMBER}?text=${encodeURIComponent(MESSAGE)}`;

export default function WhatsAppButton() {
  return (
    <a
      href={WHATSAPP_URL}
      target="_blank"
      rel="noopener noreferrer"
      aria-label="Chat with us on WhatsApp"
      style={{ position: "fixed", bottom: 24, right: 24, zIndex: 9999 }}
      className="w-[60px] h-[60px] rounded-full bg-[#25D366] text-white flex items-center justify-center shadow-lg hover:scale-105 transition"
    >
      <FaWhatsapp size={32} />
    </a>
  );
}