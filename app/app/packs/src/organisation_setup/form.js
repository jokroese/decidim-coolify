const characters = (value) => Array.from(value);
const words = (value) => value.trim().split(/\s+/u).filter(Boolean);

export const suggestShortName = (name) => {
  const normalised = words(name).join(" ");
  if (characters(normalised).length <= 12) return normalised;
  const parts = words(normalised);
  const initials = parts.map((word) => characters(word)[0]).join("").toLocaleUpperCase();
  if (parts.length > 1 && characters(initials).length >= 3 && characters(initials).length <= 12) return initials;
  let wholeWords = "";
  for (const word of parts) {
    const candidate = wholeWords ? `${wholeWords} ${word}` : word;
    if (characters(candidate).length > 12) break;
    wholeWords = candidate;
  }
  return characters(wholeWords).length >= 3 ? wholeWords : characters(normalised).slice(0, 12).join("").trim();
};

export const suggestPrefix = (name) => {
  const parts = name.normalize("NFKD").replace(/\p{M}/gu, "").match(/[\p{L}\p{N}]+/gu) || [];
  const initials = parts.map((part) => characters(part)[0]).join("");
  return initials.toLocaleUpperCase();
};

export const initialiseOrganisationSetup = (form) => {
  if (form.dataset.setupInitialised) return;
  form.dataset.setupInitialised = "true";
  const name = form.querySelector("#organization_name");
  const suggestions = [
    [form.querySelector("#organization_short_name"), suggestShortName],
    [form.querySelector("#organization_reference_prefix"), suggestPrefix]
  ].map(([input, suggest]) => ({ input, suggest, manual: input.value !== "" }));
  for (const item of suggestions) {
    item.input.addEventListener("input", () => { item.manual = true; });
  }
  name.addEventListener("input", () => {
    for (const item of suggestions) {
      if (item.manual) continue;
      item.input.value = item.suggest(name.value);
      item.input.dispatchEvent(new Event("change", { bubbles: true }));
    }
  });

  // Replace only the generic client-side hint, preserving server validation errors.
  for (const input of form.querySelectorAll("[data-setup-error]")) {
    const error = input.closest("label")?.querySelector(".form-error");
    if (error && !input.classList.contains("is-invalid-input")) error.textContent = input.dataset.setupError;
  }

  const search = form.querySelector("[data-language-search]");
  const rows = Array.from(form.querySelectorAll("[data-language-row]"));
  const filter = () => {
    const query = search.value.trim().toLocaleLowerCase();
    rows.forEach((row) => { row.hidden = !row.textContent.toLocaleLowerCase().includes(query); });
    form.querySelector("[data-no-languages]").hidden = rows.some((row) => !row.hidden);
  };
  form.querySelector("[data-language-search-wrapper]").hidden = false;
  search.addEventListener("input", filter);
  const enableDefault = () => {
    rows.forEach((row) => {
      const enabled = row.querySelector('input[type="checkbox"]');
      const selected = row.querySelector('input[type="radio"]');
      if (selected.checked) enabled.checked = true;
    });
  };
  rows.forEach((row) => row.addEventListener("change", enableDefault));
  enableDefault();
  form.addEventListener("submit", () => {
    // Restore all languages before validation so errors cannot be hidden by a search.
    search.value = "";
    filter();
    enableDefault();
  }, true);
};
