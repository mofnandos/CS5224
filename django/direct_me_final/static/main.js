function toggle() {
  var x = document.getElementById("dir-table");
  if (x.style.display === "none") {
    x.style.display = "block";
  } else {
    x.style.display = "none";
  }
}

var closeAdBtn = document.getElementById('close-ad-btn');
var adContainer = document.getElementById('ad-container');

closeAdBtn.addEventListener('click', function() {
  adContainer.style.display = 'none';
});
