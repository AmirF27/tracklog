var removeIcon = " <i class='fa fa-times' aria-hidden='true'></i>";
var timer;
var searchInput;
var resultList;

$(function() {
    searchInput = $("#game-search");
    resultList = $(".game-results");
    
    searchInput.on("keyup", function() {
        // credit for timeout idea to following StackOverflow answer:
        // http://stackoverflow.com/a/13209287
        clearTimeout(timer);
        timer = setTimeout(function() {
            if (searchInput.val()) {
                search(searchInput.val());
                resultList.show();
            }
            else {
                resultList.html("");
                resultList.hide();
            }
        }, 300);
    });
});

function search(query) {
    // http://www.ajaxload.info/
    $(".game-results").html("<img src='/static/img/ajax-loader.gif'>");

    $.getJSON(Flask.url_for("search"), { q: query }, function(data) {
        var results = [];
        data.forEach(function(game) {
            var item = "<li class='list-group-item' data-game-id='" + game.id + "'>";
            var img = {};
            if (game.cover) {
                img.src = game.cover.url;
                img.alt = game.name;
            }
            else {
                img.src = "https://placeholdit.imgix.net/~text?txtsize=22&txt=Missing%20cover&w=90&h=90";
                img.alt = "Missing cover";
            }
            item += "<img src='" + img.src + "' alt='" + img.alt + "'>";
            item += "<span>" + game.name + "</span></li>";
            results.push(item);
        });
        $(".game-results").html(
            $("<ul/>", {
                "class": "list-group search-results",
                html: results.join("")
            })
        );

        $(".search-results li").on("click", function() {
            setGameSelection({
                id: $(this).data("game-id"),
                name: $("span", this).text()
            });

            setPlatforms($(this).data("game-id"));
        });
    });
}

function setGameSelection(game) {
    $(".game-results").html("");
    $(".game-results").hide();

    $("#game-search").val("").hide();
    $(".game-panel").show();
    $(".game-panel .panel-body").html(game.name + removeIcon).attr("data-game-id", game.id);
    $(".game-results").html("");

    $(".game-panel .panel-body .fa-times").on("click", function() {
        clearGameSelection();
    });
}

function clearGameSelection() {
    $(".game-panel").hide();
    $("#game-search").show().focus();
}

function setPlatforms(id) {
    $("#platform-select").hide();
    $(".platform-loading").show();
    $.getJSON(Flask.url_for("platforms"), { id: id }, function(data) {
        var platforms = [];
        console.log(data);
        data.forEach(function(platform) {
            platforms.push(
                "<option>" + platform + "</option>");
            console.log(platform);
        });

        $("select").append(platforms.join(""));

        $(".platform-loading").hide();
        $("#platform-select").show();
    });
}
