const workspaceMenus = [...document.querySelectorAll(".app-header details")];

for (const menu of workspaceMenus) {
    menu.addEventListener("keydown", event => {
        if (event.key === "Escape" && menu.open) {
            menu.open = false;
            menu.querySelector("summary").focus();
        }
    });
    menu.addEventListener("toggle", () => {
        if (!menu.open) return;
        for (const other of workspaceMenus) {
            if (other !== menu) other.open = false;
        }
    });
}

document.addEventListener("click", event => {
    for (const menu of workspaceMenus) {
        if (menu.open && !menu.contains(event.target)) menu.open = false;
    }
});
