document.addEventListener("DOMContentLoaded", () => {
  // Fade-in effect on load
  document.body.style.opacity = 0;
  document.body.style.transition = "opacity 1s ease";
  setTimeout(() => (document.body.style.opacity = 1), 100);

  // Animate stat counters
  const counters = [
    { id: "racesBotted", target: 128379 },
    { id: "accountsBotted", target: 2412 },
    { id: "daysOnline", target: 173 },
  ];

  counters.forEach(counter => {
    animateCounter(counter.id, counter.target);
  });

  function animateCounter(id, target) {
    const el = document.getElementById(id);
    if (!el) return;
    let count = 0;
    const step = Math.ceil(target / 100); // change rate
    const interval = setInterval(() => {
      count += step;
      if (count >= target) {
        el.textContent = target.toLocaleString();
        clearInterval(interval);
      } else {
        el.textContent = count.toLocaleString();
      }
    }, 20);
  }

  // Modal toggle (for Add Task button)
  const modalTrigger = document.getElementById("addTaskBtn");
  const modal = document.getElementById("taskModal");
  const modalClose = document.getElementById("closeModal");

  if (modalTrigger && modal && modalClose) {
    modalTrigger.addEventListener("click", () => {
      modal.style.display = "flex";
      document.body.style.overflow = "hidden";
    });

    modalClose.addEventListener("click", () => {
      modal.style.display = "none";
      document.body.style.overflow = "auto";
    });

    window.addEventListener("click", (e) => {
      if (e.target === modal) {
        modal.style.display = "none";
        document.body.style.overflow = "auto";
      }
    });
  }
});
// JS Script
