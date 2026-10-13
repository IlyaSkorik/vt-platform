/**
 * Icons drawn by the brand rather than borrowed from `lucide-react`.
 *
 * The public surfaces are where the icon set is specified in the Figma file
 * itself, path by path, so these are inlined from that export instead of being
 * approximated by the nearest Lucide glyph. Everything else in the app keeps
 * using Lucide — this is not the start of a parallel icon set.
 *
 * **Why they are normalised to a 26×26 box.** The Figma export crops each glyph
 * to its own bounds, which are not the same: the moon sits in 26×26 with its own
 * breathing room, the account mark is a tight 23×23. Rendered at the same
 * `size-*` the account one would read a head taller than the moon beside it. The
 * account path is therefore translated into the moon's box, so one `size-8` on
 * the parent gives the pair the same optical weight.
 *
 * They take `currentColor`, not the `#F0F1EB` / `#F9F9F9` the export carries —
 * those are two near-identical off-whites the file is not consistent about, and
 * on the header the colour has to follow `--brand-mark` so the dark theme can
 * move it.
 *
 * Every one of them is `aria-hidden` by default. Each is a picture of something
 * the control beside it already says in words — the button's `aria-label`, the
 * `dt`'s visually-hidden text — so announcing it again is noise. A caller that
 * needs the opposite can pass `aria-hidden={false}` with a label, since the
 * spread comes last.
 */

type IconProps = React.SVGProps<SVGSVGElement>;

/** The theme switch's light-theme face: Material-style `dark_mode`, from the frame. */
export function MoonIcon(props: IconProps): React.JSX.Element {
  return (
    <svg
      viewBox="0 0 26 26"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      {...props}
    >
      <path
        d="M13.1084 23.8333C11.5917 23.8333 10.1699 23.5444 8.84279 22.9667C7.51571 22.3889 6.36015 21.608 5.37612 20.6239C4.3921 19.6399 3.61119 18.4844 3.03341 17.1573C2.45564 15.8302 2.16675 14.4083 2.16675 12.8917C2.16675 10.2555 3.00633 7.93089 4.6855 5.9177C6.36467 3.9045 8.50425 2.65416 11.1042 2.16666C10.7792 3.94206 10.8786 5.6837 11.4022 7.39157C11.9258 9.09945 12.8286 10.595 14.1105 11.8782C15.3924 13.1614 16.8865 14.0651 18.5928 14.5892C20.299 15.1132 22.0459 15.2126 23.8334 14.8874C23.364 17.4898 22.1181 19.6313 20.0959 21.3121C18.0737 22.9929 15.7445 23.8333 13.1084 23.8333ZM13.1084 22.0277C14.8417 22.0277 16.4277 21.5523 17.8661 20.6015C19.3045 19.6505 20.454 18.4137 21.3147 16.8911C19.7137 16.7466 18.1819 16.3659 16.7194 15.7489C15.2569 15.132 13.96 14.2608 12.8286 13.1354C11.6971 12.01 10.8244 10.719 10.2105 9.26249C9.59661 7.80595 9.22042 6.28323 9.08194 4.69434C7.55931 5.53104 6.32702 6.67305 5.38506 8.12039C4.44328 9.5679 3.97239 11.1583 3.97239 12.8917C3.97239 15.4295 4.86064 17.5866 6.63712 19.3629C8.41343 21.1394 10.5705 22.0277 13.1084 22.0277Z"
        fill="currentColor"
      />
    </svg>
  );
}

/** The header's account control: Material-style `account_circle`, from the frame. */
export function AccountCircleIcon(props: IconProps): React.JSX.Element {
  return (
    <svg
      viewBox="0 0 26 26"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      {...props}
    >
      {/* The export's own bounds are 23×23 starting at y=9; this centres them. */}
      <g transform="translate(1.5 -7.5)">
        <path
          d="M4.4275 26.365C5.405 25.6175 6.4975 25.0281 7.705 24.5969C8.9125 24.1656 10.1775 23.95 11.5 23.95C12.8225 23.95 14.0875 24.1656 15.295 24.5969C16.5025 25.0281 17.595 25.6175 18.5725 26.365C19.2433 25.5792 19.7656 24.6879 20.1394 23.6912C20.5131 22.6946 20.7 21.6308 20.7 20.5C20.7 17.9508 19.804 15.7802 18.0119 13.9881C16.2198 12.196 14.0492 11.3 11.5 11.3C8.95083 11.3 6.78021 12.196 4.98813 13.9881C3.19604 15.7802 2.3 17.9508 2.3 20.5C2.3 21.6308 2.48688 22.6946 2.86063 23.6912C3.23438 24.6879 3.75667 25.5792 4.4275 26.365ZM8.63937 20.4856C7.86313 19.7094 7.475 18.7558 7.475 17.625C7.475 16.4942 7.86313 15.5406 8.63937 14.7644C9.41563 13.9881 10.3692 13.6 11.5 13.6C12.6308 13.6 13.5844 13.9881 14.3606 14.7644C15.1369 15.5406 15.525 16.4942 15.525 17.625C15.525 18.7558 15.1369 19.7094 14.3606 20.4856C13.5844 21.2619 12.6308 21.65 11.5 21.65C10.3692 21.65 9.41563 21.2619 8.63937 20.4856ZM11.5 32C9.90917 32 8.41417 31.6981 7.015 31.0944C5.61583 30.4906 4.39875 29.6713 3.36375 28.6362C2.32875 27.6012 1.50937 26.3842 0.905625 24.985C0.301875 23.5858 0 22.0908 0 20.5C0 18.9092 0.301875 17.4142 0.905625 16.015C1.50937 14.6158 2.32875 13.3988 3.36375 12.3637C4.39875 11.3288 5.61583 10.5094 7.015 9.90563C8.41417 9.30187 9.90917 9 11.5 9C13.0908 9 14.5858 9.30187 15.985 9.90563C17.3842 10.5094 18.6012 11.3288 19.6362 12.3637C20.6713 13.3988 21.4906 14.6158 22.0944 16.015C22.6981 17.4142 23 18.9092 23 20.5C23 22.0908 22.6981 23.5858 22.0944 24.985C21.4906 26.3842 20.6713 27.6012 19.6362 28.6362C18.6012 29.6713 17.3842 30.4906 15.985 31.0944C14.5858 31.6981 13.0908 32 11.5 32ZM14.375 29.2544C15.2758 28.9573 16.1 28.5308 16.8475 27.975C16.1 27.4192 15.2758 26.9927 14.375 26.6956C13.4742 26.3985 12.5158 26.25 11.5 26.25C10.4842 26.25 9.52583 26.3985 8.625 26.6956C7.72417 26.9927 6.9 27.4192 6.1525 27.975C6.9 28.5308 7.72417 28.9573 8.625 29.2544C9.52583 29.5515 10.4842 29.7 11.5 29.7C12.5158 29.7 13.4742 29.5515 14.375 29.2544ZM12.7362 18.8612C13.0621 18.5354 13.225 18.1233 13.225 17.625C13.225 17.1267 13.0621 16.7146 12.7362 16.3888C12.4104 16.0629 11.9983 15.9 11.5 15.9C11.0017 15.9 10.5896 16.0629 10.2638 16.3888C9.93792 16.7146 9.775 17.1267 9.775 17.625C9.775 18.1233 9.93792 18.5354 10.2638 18.8612C10.5896 19.1871 11.0017 19.35 11.5 19.35C11.9983 19.35 12.4104 19.1871 12.7362 18.8612Z"
          fill="currentColor"
        />
      </g>
    </svg>
  );
}

/**
 * The disclosure wedge on a FAQ item — the same solid, angular chevron as the
 * carousel paddles', drawn wide and shallow rather than tall and narrow.
 *
 * 25×14, so callers size it on both axes. Pointing down is its resting state;
 * an open item turns it over with `rotate-180` rather than there being a
 * second glyph for it.
 */
export function ChevronDownIcon(props: IconProps): React.JSX.Element {
  return (
    <svg
      viewBox="0 0 25 14"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      {...props}
    >
      <path
        d="M12.5 14L0 2.27921L2.43073 0L12.5 9.42547L22.5693 0L25 2.27921L12.5 14Z"
        fill="currentColor"
      />
    </svg>
  );
}

/**
 * The carousel paddles' chevrons, drawn rather than stroked: the frame's are a
 * solid wedge 28×42, far heavier and more angular than a Lucide `ChevronRight`
 * at any stroke width. Taller than wide, so they are sized by both axes rather
 * than by a square `size-*`.
 */
export function ChevronRightIcon(props: IconProps): React.JSX.Element {
  return (
    <svg
      viewBox="0 0 28 42"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      {...props}
    >
      <path
        d="M28 21L4.55841 42L0 37.9164L18.8509 21L0 4.08363L4.55841 0L28 21Z"
        fill="currentColor"
      />
    </svg>
  );
}

/** The same wedge, mirrored. */
export function ChevronLeftIcon(props: IconProps): React.JSX.Element {
  return (
    <svg
      viewBox="0 0 28 42"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      {...props}
    >
      <path
        d="M0 21L23.4416 42L28 37.9164L9.14906 21L28 4.08363L23.4416 0L0 21Z"
        fill="currentColor"
      />
    </svg>
  );
}

/**
 * The festival card's two labels, from the frame. Both are 18 wide; the pin is a
 * pixel shorter than the calendar, so it is nudged into the calendar's 18×22 box
 * rather than given a size of its own — the two sit on adjacent rows of the same
 * list and any difference in box reads as a misalignment.
 *
 * The export paints them `#211929` at 40%. That is left to the call site as a
 * text colour, so the pair tints with the row it labels instead of carrying a
 * frozen opacity into the dark theme.
 */
export function CalendarIcon(props: IconProps): React.JSX.Element {
  return (
    <svg
      viewBox="0 0 18 22"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      {...props}
    >
      <path
        d="M1.6471 21.3889C1.20241 21.3889 0.816674 21.2122 0.489906 20.8587C0.163302 20.5051 0 20.0876 0 19.6064V3.56473C0 3.08348 0.163302 2.66613 0.489906 2.31267C0.816674 1.95922 1.20241 1.7825 1.6471 1.7825H3.0469V0H4.77627V1.7825H13.0115V0H14.7409V1.7825H16.1407C16.5854 1.7825 16.9711 1.95922 17.2979 2.31267C17.6245 2.66613 17.7878 3.08348 17.7878 3.56473V19.6064C17.7878 20.0876 17.6245 20.5051 17.2979 20.8587C16.9711 21.2122 16.5854 21.3889 16.1407 21.3889H1.6471ZM1.6471 19.6064H16.1407V8.37723H1.6471V19.6064ZM1.6471 6.595H16.1407V3.56473H1.6471V6.595ZM8.8939 12.8333C8.61391 12.8333 8.37921 12.7308 8.1898 12.5259C8.00039 12.3209 7.90569 12.0669 7.90569 11.7639C7.90569 11.4609 8.00039 11.2069 8.1898 11.0019C8.37921 10.7969 8.61391 10.6944 8.8939 10.6944C9.1739 10.6944 9.4086 10.7969 9.598 11.0019C9.78741 11.2069 9.88211 11.4609 9.88211 11.7639C9.88211 12.0669 9.78741 12.3209 9.598 12.5259C9.4086 12.7308 9.1739 12.8333 8.8939 12.8333ZM4.23696 12.5259C4.04755 12.3209 3.95285 12.0669 3.95285 11.7639C3.95285 11.4609 4.04755 11.2069 4.23696 11.0019C4.42636 10.7969 4.66106 10.6944 4.94106 10.6944C5.22105 10.6944 5.45575 10.7969 5.64516 11.0019C5.83456 11.2069 5.92927 11.4609 5.92927 11.7639C5.92927 12.0669 5.83456 12.3209 5.64516 12.5259C5.45575 12.7308 5.22105 12.8333 4.94106 12.8333C4.66106 12.8333 4.42636 12.7308 4.23696 12.5259ZM12.8467 12.8333C12.5668 12.8333 12.3321 12.7308 12.1426 12.5259C11.9532 12.3209 11.8585 12.0669 11.8585 11.7639C11.8585 11.4609 11.9532 11.2069 12.1426 11.0019C12.3321 10.7969 12.5668 10.6944 12.8467 10.6944C13.1267 10.6944 13.3614 10.7969 13.5508 11.0019C13.7403 11.2069 13.835 11.4609 13.835 11.7639C13.835 12.0669 13.7403 12.3209 13.5508 12.5259C13.3614 12.7308 13.1267 12.8333 12.8467 12.8333ZM8.8939 17.1111C8.61391 17.1111 8.37921 17.0086 8.1898 16.8036C8.00039 16.5987 7.90569 16.3447 7.90569 16.0417C7.90569 15.7387 8.00039 15.4847 8.1898 15.2797C8.37921 15.0747 8.61391 14.9722 8.8939 14.9722C9.1739 14.9722 9.4086 15.0747 9.598 15.2797C9.78741 15.4847 9.88211 15.7387 9.88211 16.0417C9.88211 16.3447 9.78741 16.5987 9.598 16.8036C9.4086 17.0086 9.1739 17.1111 8.8939 17.1111ZM4.23696 16.8036C4.04755 16.5987 3.95285 16.3447 3.95285 16.0417C3.95285 15.7387 4.04755 15.4847 4.23696 15.2797C4.42636 15.0747 4.66106 14.9722 4.94106 14.9722C5.22105 14.9722 5.45575 15.0747 5.64516 15.2797C5.83456 15.4847 5.92927 15.7387 5.92927 16.0417C5.92927 16.3447 5.83456 16.5987 5.64516 16.8036C5.45575 17.0086 5.22105 17.1111 4.94106 17.1111C4.66106 17.1111 4.42636 17.0086 4.23696 16.8036ZM12.8467 17.1111C12.5668 17.1111 12.3321 17.0086 12.1426 16.8036C11.9532 16.5987 11.8585 16.3447 11.8585 16.0417C11.8585 15.7387 11.9532 15.4847 12.1426 15.2797C12.3321 15.0747 12.5668 14.9722 12.8467 14.9722C13.1267 14.9722 13.3614 15.0747 13.5508 15.2797C13.7403 15.4847 13.835 15.7387 13.835 16.0417C13.835 16.3447 13.7403 16.5987 13.5508 16.8036C13.3614 17.0086 13.1267 17.1111 12.8467 17.1111Z"
        fill="currentColor"
      />
    </svg>
  );
}

/** The place marker, centred in the calendar's box. */
export function MapPinIcon(props: IconProps): React.JSX.Element {
  return (
    <svg
      viewBox="0 0 18 22"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      {...props}
    >
      <g transform="translate(0.47 0.9)">
        <path
          d="M9.9161 9.39452C10.2983 9.03238 10.4895 8.59587 10.4895 8.085C10.4895 7.57413 10.2983 7.13762 9.9161 6.77548C9.53385 6.41334 9.07311 6.23227 8.53388 6.23227C7.99464 6.23227 7.5339 6.41334 7.15166 6.77548C6.76941 7.13762 6.57829 7.57413 6.57829 8.085C6.57829 8.59587 6.76941 9.03238 7.15166 9.39452C7.5339 9.75666 7.99464 9.93773 8.53388 9.93773C9.07311 9.93773 9.53385 9.75666 9.9161 9.39452ZM8.53388 17.9891C10.8332 16.0016 12.534 14.1978 13.6363 12.578C14.7386 10.9583 15.2898 9.528 15.2898 8.28712C15.2898 6.35009 14.6364 4.76535 13.3296 3.53289C12.0229 2.3006 10.4243 1.68446 8.53388 1.68446C6.64345 1.68446 5.04485 2.3006 3.73811 3.53289C2.43136 4.76535 1.77798 6.35009 1.77798 8.28712C1.77798 9.528 2.33802 10.9583 3.45809 12.578C4.57816 14.1978 6.27009 16.0016 8.53388 17.9891ZM8.53388 20.2125C5.67147 17.9049 3.53356 15.7615 2.12014 13.7824C0.706712 11.8033 0 9.9715 0 8.28712C0 5.76056 0.857832 3.74773 2.5735 2.24864C4.28916 0.749547 6.27596 0 8.53388 0C10.7918 0 12.7786 0.749547 14.4943 2.24864C16.2099 3.74773 17.0678 5.76056 17.0678 8.28712C17.0678 9.9715 16.361 11.8033 14.9476 13.7824C13.5342 15.7615 11.3963 17.9049 8.53388 20.2125Z"
          fill="currentColor"
        />
      </g>
    </svg>
  );
}

/**
 * A sheet with a folded corner and two ruled lines: the mark on «Положение
 * фестиваля» and on every row of «Документы».
 *
 * 15.33×19.17 — a portrait box, like the paper it draws, so callers size it on
 * both axes. A square `size-*` would stretch it into something squarer than
 * any sheet of paper is.
 */
export function DocumentIcon(props: IconProps): React.JSX.Element {
  return (
    <svg
      viewBox="0 0 15.3333 19.1667"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      {...props}
    >
      <path
        d="M3.83333 15.3333H11.5V13.4167H3.83333V15.3333ZM3.83333 11.5H11.5V9.58333H3.83333V11.5ZM1.91667 19.1667C1.38958 19.1667 0.938368 18.979 0.563021 18.6036C0.187674 18.2283 0 17.7771 0 17.25V1.91667C0 1.38958 0.187674 0.938368 0.563021 0.563021C0.938368 0.187674 1.38958 0 1.91667 0H9.58333L15.3333 5.75V17.25C15.3333 17.7771 15.1457 18.2283 14.7703 18.6036C14.395 18.979 13.9438 19.1667 13.4167 19.1667H1.91667ZM8.625 6.70833V1.91667H1.91667V17.25H13.4167V6.70833H8.625Z"
        fill="currentColor"
      />
    </svg>
  );
}

/**
 * The calendar-with-a-clock on every nomination card: a date that has a window
 * attached to it, which is exactly what a nomination's intake is.
 *
 * 20×21 and deliberately not square — the glyph's dial hangs past the
 * calendar's bottom-right corner — so callers size it with `h-*`/`w-*` rather
 * than `size-*`, which would squash the dial back into the box.
 */
export function CalendarClockIcon(props: IconProps): React.JSX.Element {
  return (
    <svg
      viewBox="0 0 20 21"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      {...props}
    >
      <path
        d="M2 6H16V4H2V6ZM2 20C1.45 20 0.979167 19.8042 0.5875 19.4125C0.195833 19.0208 0 18.55 0 18V4C0 3.45 0.195833 2.97917 0.5875 2.5875C0.979167 2.19583 1.45 2 2 2H3V0H5V2H13V0H15V2H16C16.55 2 17.0208 2.19583 17.4125 2.5875C17.8042 2.97917 18 3.45 18 4V9.675C17.6833 9.525 17.3583 9.4 17.025 9.3C16.6917 9.2 16.35 9.125 16 9.075V8H2V18H8.3C8.41667 18.3667 8.55417 18.7167 8.7125 19.05C8.87083 19.3833 9.05833 19.7 9.275 20H2ZM11.4625 19.5375C10.4875 18.5625 10 17.3833 10 16C10 14.6167 10.4875 13.4375 11.4625 12.4625C12.4375 11.4875 13.6167 11 15 11C16.3833 11 17.5625 11.4875 18.5375 12.4625C19.5125 13.4375 20 14.6167 20 16C20 17.3833 19.5125 18.5625 18.5375 19.5375C17.5625 20.5125 16.3833 21 15 21C13.6167 21 12.4375 20.5125 11.4625 19.5375ZM16.675 18.375L17.375 17.675L15.5 15.8V13H14.5V16.2L16.675 18.375Z"
        fill="currentColor"
      />
    </svg>
  );
}

/**
 * The folded map on the two «карты» links under the festival's address.
 *
 * Exported at 18×18 inside a 24px frame — which is why the glyph is given its
 * own 18-unit box rather than the icons above's 26: a caller sizes the box, and
 * the box *is* the glyph here. The Figma export draws it 293 units down its
 * sheet, so the group lifts it back to the origin instead of the path being
 * rewritten by hand — the next re-export then diffs cleanly against this one.
 */
export function MapIcon(props: IconProps): React.JSX.Element {
  return (
    <svg
      viewBox="0 0 18 18"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      {...props}
    >
      <g transform="translate(0, -293)">
        <path
          d="M12 311L6 308.9L1.35 310.7C1.01667 310.833 0.708333 310.796 0.425 310.587C0.141667 310.379 0 310.1 0 309.75V295.75C0 295.533 0.0625 295.342 0.1875 295.175C0.3125 295.008 0.483333 294.883 0.7 294.8L6 293L12 295.1L16.65 293.3C16.9833 293.167 17.2917 293.204 17.575 293.412C17.8583 293.621 18 293.9 18 294.25V308.25C18 308.467 17.9375 308.658 17.8125 308.825C17.6875 308.992 17.5167 309.117 17.3 309.2L12 311ZM11 308.55V296.85L7 295.45V307.15L11 308.55ZM13 308.55L16 307.55V295.7L13 296.85V308.55ZM2 308.3L5 307.15V295.45L2 296.45V308.3Z"
          fill="currentColor"
        />
      </g>
    </svg>
  );
}

/**
 * Material's `open_in_new`: the mark every link that leaves the site wears —
 * the map links, a partner's website, the regulation when it is a URL rather
 * than a file.
 *
 * Decorative like the rest: the link beside it already says where it goes, and
 * "opens in a new tab" belongs in the link's own accessible name if it needs
 * saying at all.
 */
export function OpenInNewIcon(props: IconProps): React.JSX.Element {
  return (
    <svg
      viewBox="0 0 14.25 14.25"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      {...props}
    >
      <path
        d="M1.58333 14.25C1.14792 14.25 0.775174 14.095 0.465104 13.7849C0.155035 13.4748 0 13.1021 0 12.6667V1.58333C0 1.14792 0.155035 0.775174 0.465104 0.465104C0.775174 0.155035 1.14792 0 1.58333 0H7.125V1.58333H1.58333V12.6667H12.6667V7.125H14.25V12.6667C14.25 13.1021 14.095 13.4748 13.7849 13.7849C13.4748 14.095 13.1021 14.25 12.6667 14.25H1.58333ZM5.30417 10.0542L4.19583 8.94583L11.5583 1.58333H8.70833V0H14.25V5.54167H12.6667V2.69167L5.30417 10.0542Z"
        fill="currentColor"
      />
    </svg>
  );
}

/**
 * The theme switch's dark-theme face, the moon's counterpart. 29×29 in the
 * export against the moon's 26×26, and its rays reach the very edge of that box
 * while the crescent keeps a margin — so it is scaled into the moon's box rather
 * than given its own, or the switch would jump size when it is flipped.
 */
export function SunIcon(props: IconProps): React.JSX.Element {
  return (
    <svg
      viewBox="-1.5 -1.5 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      {...props}
    >
      <path
        d="M12.9167 5.16667V0H15.5V5.16667H12.9167ZM21.5063 8.71875L19.7302 6.94271L23.3469 3.22917L25.1552 5.06979L21.5063 8.71875ZM23.25 15.5V12.9167H28.4167V15.5H23.25ZM12.9167 28.4167V23.25H15.5V28.4167H12.9167ZM6.91042 8.65417L3.22917 5.06979L5.06979 3.26146L8.71875 6.91042L6.91042 8.65417ZM23.3146 25.1875L19.7302 21.474L21.474 19.7302L25.1552 23.2823L23.3146 25.1875ZM0 15.5V12.9167H5.16667V15.5H0ZM5.06979 25.1875L3.26146 23.3469L6.87813 19.7302L7.81458 20.6021L8.75104 21.5063L5.06979 25.1875ZM8.71875 19.6979C7.21181 18.191 6.45833 16.3611 6.45833 14.2083C6.45833 12.0556 7.21181 10.2257 8.71875 8.71875C10.2257 7.21181 12.0556 6.45833 14.2083 6.45833C16.3611 6.45833 18.191 7.21181 19.6979 8.71875C21.2049 10.2257 21.9583 12.0556 21.9583 14.2083C21.9583 16.3611 21.2049 18.191 19.6979 19.6979C18.191 21.2049 16.3611 21.9583 14.2083 21.9583C12.0556 21.9583 10.2257 21.2049 8.71875 19.6979ZM17.8573 17.8573C18.8691 16.8455 19.375 15.6292 19.375 14.2083C19.375 12.7875 18.8691 11.5712 17.8573 10.5594C16.8455 9.54757 15.6292 9.04167 14.2083 9.04167C12.7875 9.04167 11.5712 9.54757 10.5594 10.5594C9.54757 11.5712 9.04167 12.7875 9.04167 14.2083C9.04167 15.6292 9.54757 16.8455 10.5594 17.8573C11.5712 18.8691 12.7875 19.375 14.2083 19.375C15.6292 19.375 16.8455 18.8691 17.8573 17.8573Z"
        fill="currentColor"
      />
    </svg>
  );
}

/**
 * The catalogue band's magnifier, 25×26 — heavier and rounder than Lucide's
 * `Search` at any stroke width, and drawn as a filled path rather than stroked.
 */
export function SearchIcon(props: IconProps): React.JSX.Element {
  return (
    <svg
      viewBox="0 0 25 26"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      {...props}
    >
      <path
        d="M23.3333 26L14.3288 16.6353C13.6344 17.2451 12.828 17.7226 11.9097 18.0678C10.9914 18.4128 10.0154 18.5853 8.9816 18.5853C6.47373 18.5853 4.34988 17.6805 2.61007 15.8708C0.870023 14.0614 0 11.8688 0 9.29283C0 6.71691 0.870023 4.52412 2.61007 2.71447C4.34988 0.904823 6.46597 0 8.95833 0C11.4352 0 13.5397 0.904823 15.2719 2.71447C17.0043 4.52412 17.8705 6.71691 17.8705 9.29283C17.8705 10.336 17.7084 11.335 17.3844 12.2901C17.0603 13.2448 16.5896 14.1235 15.9722 14.9262L25 24.2667L23.3333 26ZM8.95833 16.1778C10.787 16.1778 12.3438 15.5057 13.6285 14.1617C14.9132 12.8176 15.5556 11.1947 15.5556 9.29283C15.5556 7.39098 14.9132 5.76791 13.6285 4.42361C12.3438 3.07956 10.787 2.40753 8.95833 2.40753C7.11412 2.40753 5.54583 3.07956 4.25347 4.42361C2.96111 5.76791 2.31493 7.39098 2.31493 9.29283C2.31493 11.1947 2.96111 12.8176 4.25347 14.1617C5.54583 15.5057 7.11412 16.1778 8.95833 16.1778Z"
        fill="currentColor"
      />
    </svg>
  );
}

/**
 * The catalogue's filters mark — three sliders, drawn lying down. Already
 * rotated in the export, so unlike the frame's own layer it needs no transform
 * of its own; the clip path that came with that rotation is dropped with it.
 */
export function FiltersIcon(props: IconProps): React.JSX.Element {
  return (
    <svg
      viewBox="0 0 42 30"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      {...props}
    >
      <path
        d="M34.2455 23.3388H21.8602V25.8407H19.0063V18.7859H21.8602V21.2878H34.2455V23.3388ZM16.1523 23.3388H6.84912V21.2878H16.1523V23.3388ZM14.9824 18.2937H12.1285V15.7914H6.84912V13.7408H12.1285V11.2386H14.9824L14.9824 18.2937ZM34.2455 15.7914L17.8363 15.7914V13.7408L34.2455 13.7408V15.7914ZM34.2455 8.24442H28.9087V10.7464L26.0552 10.7464L26.0552 3.69153H28.9087L28.9087 6.19346H34.2455V8.24442ZM23.2013 8.24442H6.84912V6.19346H23.2013V8.24442Z"
        fill="currentColor"
      />
    </svg>
  );
}

/** The arrow on the catalogue's «Подать заявку», 28×28 — blunter and shorter in
 * the shaft than Lucide's, which at this size read as a hairline beside an 18px
 * bold label. */
export function ArrowRightIcon(props: IconProps): React.JSX.Element {
  return (
    <svg
      viewBox="0 0 28 28"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      {...props}
    >
      <path
        d="M16.3334 20.9612L14.9529 19.5805L19.6 14.9333H4.66669V12.9888H19.6L14.9334 8.32212L16.3138 6.94167L23.3334 13.9612L16.3334 20.9612Z"
        fill="currentColor"
      />
    </svg>
  );
}
