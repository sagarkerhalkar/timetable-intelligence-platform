"use client";

function whatsappUrl(recipient: string, message: string): string {
  if (recipient === "choose_in_whatsapp" || recipient === "No recipient") {
    return `https://wa.me/?text=${encodeURIComponent(message)}`;
  }
  let digits = recipient.replace(/\D/g, "");
  if (digits.length === 10) digits = `91${digits}`;
  return `https://wa.me/${digits}?text=${encodeURIComponent(message)}`;
}

export function PersonalWhatsAppButton({ recipient, message }: Readonly<{ recipient: string; message: string }>) {
  return <a className="button secondary compact" href={whatsappUrl(recipient, message)} target="_blank" rel="noreferrer">Open WhatsApp</a>;
}
