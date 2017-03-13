var removeIcon = " <i class='fa fa-times' aria-hidden='true'></i>";
var xhrPool = [];

$(function() {
    $("#game-search").on("input", function() {
        if (this.value) {
            search($(this).val());
        }
        else {
            $(".game-results").html("");
            xhrPool.forEach(function(xhr) {
                xhr.abort();
            });
            xhrPool = [];
        }
    });
});

function search(query) {
    // http://www.ajaxload.info/
    $(".game-results").html("<img src='/static/img/ajax-loader.gif'>");
    xhr = $.getJSON(Flask.url_for("search"), { q: query }, function(data) {
        var results = [];
        data.forEach(function(game) {
            results.push(
                "<li class='list-group-item' data-game-id='" + game.id + "'>" + 
                "<img src='" + game.cover.url + "' alt='" + game.name + "'>" + 
                "<span>" + game.name + "</span>" + 
                "</li>");
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

    xhrPool.push(xhr);
}

function setGameSelection(game) {
    xhrPool.forEach(function(xhr) {
        xhr.abort();
    });
    xhrPool = [];

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
    $.getJSON(Flask.url_for("platforms"), { id: id }, function(data) {
        var platforms = [];
        console.log(data);
        data.forEach(function(platform) {
            platforms.push(
                "<option>" + platform + "</option>");
            console.log(platform);
        });

        $("select").append(platforms.join(""));
    });
}
