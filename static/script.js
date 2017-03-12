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
                "<li class='list-group-item'>" + 
                "<img src='" + game.cover.url + "' alt='" + game.name + "'>" + 
                game.name + 
                "</li>");
        });
        $(".game-results").html(
            $("<ul/>", {
                "class": "list-group",
                html: results.join("")
            })
        );

        // $("<ul/>", {
        //     "class": "list-group",
        //     html: results.join("")
        // }).appendTo(".game-results");
    });
}
