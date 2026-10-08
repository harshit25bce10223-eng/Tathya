export function BrandFilters() {
  return (
    <svg
      width="0"
      height="0"
      aria-hidden="true"
      style={{ position: "absolute" }}
    >
      <defs>
        <filter id="brand-paper" colorInterpolationFilters="sRGB">
          <feColorMatrix
            type="matrix"
            values="1 0 0 0 0 0 1 0 0 0 0 0 1 0 0 -1 -1 -1 0 2.7"
          />
        </filter>
        <filter id="brand-gold" colorInterpolationFilters="sRGB">
          <feColorMatrix
            type="matrix"
            values="1 0 0 0 0 0 1 0 0 0 0 0 1 0 0 2 0 -2 0 -.3"
          />
        </filter>
      </defs>
    </svg>
  )
}
