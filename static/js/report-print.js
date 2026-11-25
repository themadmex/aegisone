const printButton = document.querySelector("[data-print-report]");
if (printButton) {
    printButton.hidden = false;
    printButton.addEventListener("click", () => window.print());
}
