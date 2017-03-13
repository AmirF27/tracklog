var removeIcon = " <i class='fa fa-times' aria-hidden='true'></i>";

$(function() {
    $("#game-search").on("input", function() {
        search($(this).val());
    });

    
});

function search(query) {
    $.getJSON(Flask.url_for("search"), { q: query })
    .then(function(data) {
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
                "class": "list-group",
                html: results.join("")
            })
        );

        $("li").on("click", function() {
            chooseGame({
                id: $(this).data("game-id"),
                name: $("span", this).text()
            });
        });
    });
}

function chooseGame(game) {
    $("#game-search").hide();
    $(".game-panel").show();
    $(".game-panel .panel-body").html(game.name + removeIcon).attr("data-game-id", game.id);
}
