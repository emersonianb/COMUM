const canvas = document.getElementById('world-map-canvas');
const ctx = canvas.getContext('2d');

let width, height;
let squares = [];

// Tamanho dos blocos interativos
const squareMinSize = 14;
const squareMaxSize = 24;
const densityStep = 18;

class Square {
    constructor(targetX, targetY) {
        this.x = Math.random() * width;
        this.y = Math.random() * height;
        
        this.targetX = targetX;
        this.targetY = targetY;

        this.size = Math.random() * (squareMaxSize - squareMinSize) + squareMinSize;
        this.alpha = Math.random() * 0.5 + 0.3;
        this.color = Math.random() > 0.6 ? '#F4442E' : (Math.random() > 0.3 ? '#FC9E4F' : '#EDD382');
        
        this.ease = 0.02 + Math.random() * 0.02;
    }

    update(mouseX, mouseY) {
        this.x += (this.targetX - this.x) * this.ease;
        this.y += (this.targetY - this.y) * this.ease;

        if (mouseX && mouseY) {
            let dx = mouseX - this.x;
            let dy = mouseY - this.y;
            let dist = Math.sqrt(dx * dx + dy * dy);
            if (dist < 150) {
                let angle = Math.atan2(dy, dx);
                let force = (150 - dist) * 0.35;
                this.x -= Math.cos(angle) * force;
                this.y -= Math.sin(angle) * force;
            }
        }
    }

    draw() {
        ctx.save();
        ctx.fillStyle = this.color;
        ctx.globalAlpha = this.alpha;
        ctx.shadowBlur = 12;
        ctx.shadowColor = this.color;
        ctx.fillRect(this.x, this.y, this.size, this.size);
        ctx.restore();
    }
}

let worldMapPoints = [];
const mapImage = new Image();
mapImage.crossOrigin = "Anonymous";
mapImage.src = "https://upload.wikimedia.org/wikipedia/commons/8/80/World_map_-_low_resolution.svg";

mapImage.onload = () => {
    generateMapPoints();
    resize();
};

function generateMapPoints() {
    const tempCanvas = document.createElement('canvas');
    const tempCtx = tempCanvas.getContext('2d');
    
    const mapWidth = 900;
    const mapHeight = 450;
    
    tempCanvas.width = mapWidth;
    tempCanvas.height = mapHeight;
    
    tempCtx.drawImage(mapImage, 0, 0, mapWidth, mapHeight);
    
    const imgData = tempCtx.getImageData(0, 0, mapWidth, mapHeight).data;
    worldMapPoints = [];

    for (let y = 0; y < mapHeight; y += densityStep) {
        for (let x = 0; x < mapWidth; x += densityStep) {
            const alphaIndex = (y * mapWidth + x) * 4 + 3;
            if (imgData[alphaIndex] > 50) {
                worldMapPoints.push({
                    relX: x / mapWidth,
                    relY: y / mapHeight
                });
            }
        }
    }
    
    initSquares();
}

function resize() {
    width = canvas.width = window.innerWidth;
    height = canvas.height = window.innerHeight;
    initSquares();
}

function initSquares() {
    if (worldMapPoints.length === 0) return;
    
    squares = [];
    
    const renderWidth = Math.min(width * 0.85, 1200);
    const renderHeight = renderWidth / 2;
    
    const startX = (width - renderWidth) / 2;
    const startY = (height - renderHeight) / 2 - 20;

    worldMapPoints.forEach(point => {
        let targetX = startX + point.relX * renderWidth;
        let targetY = startY + point.relY * renderHeight;
        
        targetX += (Math.random() * 8 - 4);
        targetY += (Math.random() * 8 - 4);

        squares.push(new Square(targetX, targetY));
    });
}

let mouse = { x: null, y: null };

window.addEventListener('mousemove', (e) => {
    mouse.x = e.clientX;
    mouse.y = e.clientY;
});

window.addEventListener('mouseleave', () => {
    mouse.x = null;
    mouse.y = null;
});

function animate() {
    ctx.clearRect(0, 0, width, height);
    
    squares.forEach(sq => {
        sq.update(mouse.x, mouse.y);
        sq.draw();
    });

    requestAnimationFrame(animate);
}

window.addEventListener('resize', resize);
animate();

// 🌍 ANIMAÇÃO DO TÍTULO MULTILINGUE (Apenas no carregamento da página)
document.addEventListener('DOMContentLoaded', () => {
    const titleElement = document.querySelector('.hero-content h1');
    if (!titleElement) return;

    const languages = [
        { word: "common" },
        { word: "κοινός" },
        { word: "commun" },
        { word: "普通" },
        { word: "communis" },
        { word: "一般" },
        { word: "comum" }
    ];

    let currentIndex = 0;

    const changeLanguage = () => {
        if (currentIndex < languages.length) {
            titleElement.style.opacity = '0.2';
            
            setTimeout(() => {
                titleElement.textContent = languages[currentIndex].word;
                titleElement.style.opacity = '1';
                currentIndex++;
                
                if (currentIndex < languages.length) {
                    setTimeout(changeLanguage, 250); // Velocidade do ciclo
                }
            }, 80);
        }
    };

    // Executa apenas uma vez ao carregar a página
    changeLanguage();
});