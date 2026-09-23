import "./globals.css";
import { CartProvider } from "@/context/CartContext";
import { LocationProvider } from "@/context/LocationContext";
import { SearchProvider } from "@/context/SearchContext";
import { UserProvider } from "@/context/UserContext";
import Header from "@/components/Header";
import CartDrawer from "@/components/CartDrawer";
import MobileCartBar from "@/components/MobileCartBar";
import LocationModal from "@/components/LocationModal";
import SearchModal from "@/components/SearchModal";
import AuthModal from "@/components/AuthModal";

export const metadata = {
  title: "Wok & Bun — Fast Food, Chinese & More | DHA Phase II, Islamabad",
  description:
    "Wok & Bun serves gourmet smash burgers, Nashville tenders, loaded fries, pizza, pasta, seafood and authentic Chinese in DHA Phase II, Islamabad. Order online for delivery.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="bg-bg text-ink min-h-screen">
        <LocationProvider>
          <SearchProvider>
            <UserProvider>
              <CartProvider>
                <Header />
                <main className="pb-24 md:pb-10">{children}</main>
                <CartDrawer />
                <MobileCartBar />
                <LocationModal />
                <SearchModal />
                <AuthModal />
              </CartProvider>
            </UserProvider>
          </SearchProvider>
        </LocationProvider>
      </body>
    </html>
  );
}