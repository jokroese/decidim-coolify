import { initialiseOrganisationSetup } from "../src/organisation_setup/form";

const initialise = () => document.querySelectorAll("[data-organisation-setup]").forEach(initialiseOrganisationSetup);
if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initialise);
else initialise();
document.addEventListener("turbo:load", initialise);
