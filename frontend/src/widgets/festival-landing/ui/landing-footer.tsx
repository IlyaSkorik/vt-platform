import { ExternalLink, Globe, Mail, MapPin, Phone } from "lucide-react";
import type { FestivalContacts } from "@/features/festival-landing";

interface ContactLinkProps {
  icon: React.ComponentType<{ className?: string }>;
  href: string;
  external?: boolean;
  children: React.ReactNode;
}

function ContactLink({
  icon: Icon,
  href,
  external = false,
  children,
}: ContactLinkProps): React.JSX.Element {
  const externalProps = external ? { target: "_blank", rel: "noopener noreferrer" } : {};
  return (
    <a
      href={href}
      {...externalProps}
      className="inline-flex items-center gap-2 rounded outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring"
    >
      <Icon className="size-4 shrink-0" aria-hidden="true" />
      <span className="truncate">{children}</span>
    </a>
  );
}

interface SocialLink {
  label: string;
  href: string;
}

function socialLinks(contacts: FestivalContacts): SocialLink[] {
  const links: SocialLink[] = [];
  if (contacts.social.vk) {
    links.push({ label: "ВКонтакте", href: contacts.social.vk });
  }
  if (contacts.social.telegram) {
    links.push({ label: "Telegram", href: contacts.social.telegram });
  }
  if (contacts.social.instagram) {
    links.push({ label: "Instagram", href: contacts.social.instagram });
  }
  return links;
}

interface LandingFooterProps {
  contacts: FestivalContacts;
}

/**
 * The public footer: organizer contacts, social links, website and team.
 *
 * Reuses Competition Contacts verbatim — the same configuration that powers the
 * catalog and the venue section. Columns render only when they carry content.
 */
export function LandingFooter({ contacts }: LandingFooterProps): React.JSX.Element {
  const social = socialLinks(contacts);
  const hasContacts = Boolean(contacts.phone || contacts.email || contacts.address);
  const hasReach = Boolean(contacts.website) || social.length > 0;

  return (
    <footer className="rounded-2xl border bg-muted/40 p-6 sm:p-8">
      <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
        <div className="space-y-3">
          <p className="text-base font-semibold text-foreground">
            {contacts.organizationName ?? "Организатор"}
          </p>
          {hasContacts ? (
            <div className="flex flex-col items-start gap-2 text-sm text-muted-foreground">
              {contacts.address ? (
                <p className="flex items-start gap-2">
                  <MapPin className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
                  <span>{contacts.address}</span>
                </p>
              ) : null}
              {contacts.phone ? (
                <ContactLink icon={Phone} href={`tel:${contacts.phone}`}>
                  {contacts.phone}
                </ContactLink>
              ) : null}
              {contacts.email ? (
                <ContactLink icon={Mail} href={`mailto:${contacts.email}`}>
                  {contacts.email}
                </ContactLink>
              ) : null}
            </div>
          ) : null}
        </div>

        {hasReach ? (
          <div className="space-y-3">
            <p className="text-sm font-semibold text-foreground">Ссылки</p>
            <div className="flex flex-col items-start gap-2 text-sm text-muted-foreground">
              {contacts.website ? (
                <ContactLink icon={Globe} href={contacts.website} external>
                  Сайт фестиваля
                </ContactLink>
              ) : null}
              {social.map((link) => (
                <ContactLink key={link.href} icon={ExternalLink} href={link.href} external>
                  {link.label}
                </ContactLink>
              ))}
            </div>
          </div>
        ) : null}

        {contacts.team.length > 0 ? (
          <div className="space-y-3">
            <p className="text-sm font-semibold text-foreground">Контактные лица</p>
            <ul className="space-y-3 text-sm">
              {contacts.team.map((member) => (
                <li key={member.id} className="space-y-0.5">
                  <p className="font-medium text-foreground">{member.name}</p>
                  {member.position ? (
                    <p className="text-muted-foreground">{member.position}</p>
                  ) : null}
                  <div className="flex flex-wrap gap-x-4 gap-y-1 text-muted-foreground">
                    {member.phone ? (
                      <ContactLink icon={Phone} href={`tel:${member.phone}`}>
                        {member.phone}
                      </ContactLink>
                    ) : null}
                    {member.email ? (
                      <ContactLink icon={Mail} href={`mailto:${member.email}`}>
                        {member.email}
                      </ContactLink>
                    ) : null}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
    </footer>
  );
}
