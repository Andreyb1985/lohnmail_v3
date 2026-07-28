import Image from "next/image";

export default function BrandLogo() {
  return (
    <>
      <Image className="logo-image" src="/lohnmail-icon.png" alt="" width={36} height={36} priority />
      <span className="logo-word">Lohn<span>Mail</span></span>
    </>
  );
}
