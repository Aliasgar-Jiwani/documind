// DOM elements
const fileTypeSelect = document.getElementById("file-type");
const uploadTabBtn = document.getElementById("upload-tab-btn");
const pasteTabBtn = document.getElementById("paste-tab-btn");
const uploadTab = document.getElementById("upload-tab");
const pasteTab = document.getElementById("paste-tab");
const fileDrop = document.getElementById("file-drop");
const fileUpload = document.getElementById("file-upload");
const fileInfo = document.getElementById("file-info");
const fileRemove = document.getElementById("file-remove");
const fileTypeIcon = document.getElementById("file-type-icon");
const fileName = document.getElementById("file-name");
const fileSize = document.getElementById("file-size");
const fileContent = document.getElementById("file-content");
const explainBtn = document.getElementById("explain-btn");
const loading = document.getElementById("loading");
const progressBar = document.getElementById("progress-bar");
const explanationOutput = document.getElementById("explanation-output");
const statusDiv = document.getElementById("status");
const copyBtn = document.getElementById("copy-btn");
const downloadBtn = document.getElementById("download-btn");
const themeToggle = document.getElementById("theme-toggle");

// Global variables
let currentFile = null;
const API_URL = "http://localhost:8000/explain";
const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB

// Initialize particles.js
particlesJS("particles-js", {
  particles: {
    number: {
      value: 30,
      density: {
        enable: true,
        value_area: 800,
      },
    },
    color: {
      value: "#6366f1",
    },
    shape: {
      type: "circle",
      stroke: {
        width: 0,
        color: "#000000",
      },
    },
    opacity: {
      value: 0.3,
      random: true,
      anim: {
        enable: true,
        speed: 1,
        opacity_min: 0.1,
        sync: false,
      },
    },
    size: {
      value: 5,
      random: true,
      anim: {
        enable: true,
        speed: 2,
        size_min: 0.1,
        sync: false,
      },
    },
    line_linked: {
      enable: true,
      distance: 150,
      color: "#6366f1",
      opacity: 0.2,
      width: 1,
    },
    move: {
      enable: true,
      speed: 1,
      direction: "none",
      random: true,
      straight: false,
      out_mode: "out",
      bounce: false,
      attract: {
        enable: false,
        rotateX: 600,
        rotateY: 1200,
      },
    },
  },
  interactivity: {
    detect_on: "canvas",
    events: {
      onhover: {
        enable: true,
        mode: "grab",
      },
      onclick: {
        enable: true,
        mode: "push",
      },
      resize: true,
    },
    modes: {
      grab: {
        distance: 140,
        line_linked: {
          opacity: 0.5,
        },
      },
      push: {
        particles_nb: 3,
      },
    },
  },
  retina_detect: true,
});

// Theme toggle
themeToggle.addEventListener("click", () => {
  document.body.classList.toggle("dark-mode");
  const icon = themeToggle.querySelector("i");
  if (document.body.classList.contains("dark-mode")) {
    icon.classList.remove("fa-moon");
    icon.classList.add("fa-sun");
  } else {
    icon.classList.remove("fa-sun");
    icon.classList.add("fa-moon");
  }
});

// Button ripple effect
document.querySelectorAll(".button").forEach((button) => {
  button.addEventListener("click", function (e) {
    if (this.disabled) return;

    const x = e.clientX - e.target.getBoundingClientRect().left;
    const y = e.clientY - e.target.getBoundingClientRect().top;

    const ripple = document.createElement("span");
    ripple.classList.add("button-ripple");
    ripple.style.left = `${x}px`;
    ripple.style.top = `${y}px`;

    this.appendChild(ripple);

    setTimeout(() => {
      ripple.remove();
    }, 600);
  });
});

// Tab switching
uploadTabBtn.addEventListener("click", () => {
  uploadTabBtn.classList.add("active");
  pasteTabBtn.classList.remove("active");
  uploadTab.classList.add("active");
  pasteTab.classList.remove("active");
  updateExplainButtonState();
});

pasteTabBtn.addEventListener("click", () => {
  pasteTabBtn.classList.add("active");
  uploadTabBtn.classList.remove("active");
  pasteTab.classList.add("active");
  uploadTab.classList.remove("active");
  updateExplainButtonState();
});

// File upload handling
fileDrop.addEventListener("click", () => {
  fileUpload.click();
});

fileDrop.addEventListener("dragover", (e) => {
  e.preventDefault();
  fileDrop.classList.add("dragover");
});

fileDrop.addEventListener("dragleave", () => {
  fileDrop.classList.remove("dragover");
});

fileDrop.addEventListener("drop", (e) => {
  e.preventDefault();
  fileDrop.classList.remove("dragover");

  if (e.dataTransfer.files.length) {
    handleFileUpload(e.dataTransfer.files[0]);
  }
});

fileUpload.addEventListener("change", (e) => {
  if (e.target.files.length > 0) {
    handleFileUpload(e.target.files[0]);
  }
});

fileRemove.addEventListener("click", () => {
  currentFile = null;
  fileInfo.style.display = "none";
  fileUpload.value = "";
  updateExplainButtonState();
});

function handleFileUpload(file) {
  if (file.size > MAX_FILE_SIZE) {
    showStatus("File is too large. Maximum size is 5MB.", "error");
    return;
  }

  currentFile = file;

  // Update file type based on uploaded file extension
  const extension = file.name.split(".").pop().toLowerCase();
  let fileIconClass = "file-type-other";
  let fileIconHTML = '<i class="fas fa-file"></i>';

  switch (extension) {
    case "py":
      fileTypeSelect.value = "python";
      fileIconClass = "file-type-py";
      fileIconHTML = '<i class="fab fa-python"></i>';
      break;
    case "js":
      fileTypeSelect.value = "javascript";
      fileIconClass = "file-type-js";
      fileIconHTML = '<i class="fab fa-js"></i>';
      break;
    case "html":
      fileTypeSelect.value = "html";
      fileIconClass = "file-type-html";
      fileIconHTML = '<i class="fab fa-html5"></i>';
      break;
    case "css":
      fileTypeSelect.value = "css";
      fileIconClass = "file-type-css";
      fileIconHTML = '<i class="fab fa-css3-alt"></i>';
      break;
    case "json":
      fileTypeSelect.value = "json";
      fileIconClass = "file-type-json";
      fileIconHTML = '<i class="fas fa-code"></i>';
      break;
    case "yml":
    case "yaml":
      fileTypeSelect.value = "yaml";
      fileIconClass = "file-type-other";
      fileIconHTML = '<i class="fas fa-file-code"></i>';
      break;
    case "md":
      fileTypeSelect.value = "markdown";
      fileIconClass = "file-type-md";
      fileIconHTML = '<i class="fab fa-markdown"></i>';
      break;
    case "txt":
      fileTypeSelect.value = "text";
      fileIconClass = "file-type-txt";
      fileIconHTML = '<i class="fas fa-file-alt"></i>';
      break;
    case "sh":
      fileTypeSelect.value = "bash";
      fileIconClass = "file-type-sh";
      fileIconHTML = '<i class="fas fa-terminal"></i>';
      break;
    case "conf":
    case "cfg":
    case "ini":
      fileTypeSelect.value = "configuration";
      fileIconClass = "file-type-other";
      fileIconHTML = '<i class="fas fa-cog"></i>';
      break;
    default:
      fileTypeSelect.value = "other";
  }

  // Show file info
  fileInfo.style.display = "block";
  fileName.textContent = file.name;
  fileSize.textContent = formatFileSize(file.size);

  // Update file icon
  fileTypeIcon.className = `file-type-icon ${fileIconClass}`;
  fileTypeIcon.innerHTML = fileIconHTML;

  updateExplainButtonState();
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + " bytes";
  else if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
  else return (bytes / 1048576).toFixed(1) + " MB";
}

// Text area input handling
fileContent.addEventListener("input", updateExplainButtonState);

// Update explain button state
function updateExplainButtonState() {
  if (uploadTab.classList.contains("active")) {
    explainBtn.disabled = !currentFile;
  } else {
    explainBtn.disabled = !fileContent.value.trim();
  }
}

// Copy button
copyBtn.addEventListener("click", () => {
  const text = explanationOutput.textContent;
  navigator.clipboard
    .writeText(text)
    .then(() => {
      showStatus("Copied to clipboard!", "success");
    })
    .catch((err) => {
      showStatus("Failed to copy: " + err, "error");
    });
});

// Download button
downloadBtn.addEventListener("click", () => {
  const text = explanationOutput.textContent;
  const blob = new Blob([text], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "explanation.txt";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
});

// Explain button click handler
explainBtn.addEventListener("click", async () => {
  // Get file content
  let content = "";
  if (uploadTab.classList.contains("active")) {
    if (!currentFile) return;

    try {
      content = await readFile(currentFile);
    } catch (error) {
      showStatus("Error reading file: " + error.message, "error");
      return;
    }
  } else {
    content = fileContent.value.trim();
    if (!content) return;
  }

  // Get file type
  const fileType = fileTypeSelect.value;

  // Show loading
  loading.style.display = "flex";
  explanationOutput.style.display = "none";
  statusDiv.style.display = "none";
  explainBtn.disabled = true;

  // Simulate progress
  let progress = 0;
  const progressInterval = setInterval(() => {
    progress += Math.random() * 5;
    if (progress > 90) progress = 90;
    progressBar.style.width = progress + "%";
  }, 300);

  // Send to API
  try {
    const response = await fetch(API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        file_content: content,
        file_type: fileType,
      }),
    });

    const data = await response.json();

    if (!response.ok || data.status === "error") {
      throw new Error(data.error || "Unknown error occurred");
    }

    // Complete progress
    progress = 100;
    progressBar.style.width = progress + "%";

    // Show explanation with typing effect
    explanationOutput.style.display = "block";
    explanationOutput.innerHTML = "";

    const explanation = data.explanation || "No explanation provided";

    // Add typing effect
    let i = 0;
    const typeInterval = setInterval(() => {
      if (i < explanation.length) {
        explanationOutput.innerHTML += explanation.charAt(i);
        explanationOutput.scrollTop = explanationOutput.scrollHeight;
        i++;
      } else {
        clearInterval(typeInterval);
        explanationOutput.classList.remove("typing");

        // Highlight code blocks or important parts
        highlightCodeBlocks();

        showStatus(
          '<i class="fas fa-check-circle"></i> Explanation generated successfully!',
          "success"
        );
      }
    }, 5);

    explanationOutput.classList.add("typing");
  } catch (error) {
    showStatus(
      '<i class="fas fa-exclamation-triangle"></i> Error: ' + error.message,
      "error"
    );
    explanationOutput.textContent =
      "Failed to generate explanation. Please try again.";
    explanationOutput.style.display = "block";
  } finally {
    // Hide loading
    clearInterval(progressInterval);
    setTimeout(() => {
      loading.style.display = "none";
      explainBtn.disabled = false;
    }, 500);
  }
});

function readFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();

    reader.onload = (event) => {
      resolve(event.target.result);
    };

    reader.onerror = (error) => {
      reject(error);
    };

    reader.readAsText(file);
  });
}

function showStatus(message, type) {
  statusDiv.innerHTML = message;
  statusDiv.className = "status " + type;
  statusDiv.style.display = "block";

  // Auto hide after 5 seconds
  setTimeout(() => {
    statusDiv.style.display = "none";
  }, 5000);
}

function highlightCodeBlocks() {
  // Simple code block highlighting
  // This is a basic implementation - in a real app you might use a library like highlight.js
  const content = explanationOutput.innerHTML;
  const highlightedContent = content
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\`\`\`([^`]+)\`\`\`/g, '<div class="highlight">$1</div>');

  explanationOutput.innerHTML = highlightedContent;
}
