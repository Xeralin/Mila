pragma ComponentBehavior: Bound
import QtQuick
import ".."

Item {
    id: control

    property var options: []
    property var current_value
    signal picked(var value)

    readonly property int _count: options ? options.length : 0
    readonly property int _index: {
        for (var i = 0; i < _count; i++) {
            if (options[i].value === current_value)
                return i
        }
        return -1
    }
    readonly property bool _red: row_hover.hovered
    readonly property bool _down: left_tap.pressed || right_tap.pressed
    readonly property color _grad_clear: Qt.alpha(Theme.accent, 0)
    readonly property color _grad_mid: Qt.alpha(Qt.darker(Theme.accent, _down ? 2.2 : 2.0), 0.85)
    readonly property color _grad_bot: _down ? Theme.accent_pressed : Qt.darker(Theme.accent, 1.2)

    property string neighbors: "horizontal"
    readonly property real _grow_x: neighbors === "horizontal" ? 12 : 6
    readonly property real _grow_y: neighbors === "vertical" ? 12 : 6
    readonly property real _cap_x: neighbors === "horizontal" ? 1 : 0.1
    readonly property real _cap_y: neighbors === "vertical" ? 1 : 0.1

    function _step(delta) {
        if (_count === 0)
            return
        var base = _index < 0 ? 0 : _index
        picked(options[(base + delta + _count) % _count].value)
    }

    function _pick(i) {
        if (i >= 0 && i < _count)
            picked(options[i].value)
    }

    implicitWidth: 130
    implicitHeight: 46
    activeFocusOnTab: true
    opacity: enabled ? 1.0 : 0.4

    Keys.onLeftPressed: _step(-1)
    Keys.onRightPressed: _step(1)

    HoverHandler { id: row_hover }

    Item {
        id: surface
        anchors.fill: parent

        transform: Scale {
            origin.x: control.width / 2
            origin.y: control.height / 2
            xScale: control._red ? 1 + Math.min(control._grow_x / control.width, control._cap_x) : 1.0
            yScale: control._red ? 1 + Math.min(control._grow_y / control.height, control._cap_y) : 1.0

            Behavior on xScale { NumberAnimation { duration: 60; easing.type: Easing.Linear } }
            Behavior on yScale { NumberAnimation { duration: 60; easing.type: Easing.Linear } }
        }

        Rectangle {
            anchors.fill: parent
            radius: Theme.radius_small
            color: control._red ? Theme.button_fill_solid : Theme.button_fill
        }

        Rectangle {
            anchors.fill: parent
            radius: Theme.radius_small
            visible: control._red
            gradient: Gradient {
                GradientStop {
                    position: 0.0
                    color: control._grad_clear
                }
                GradientStop {
                    position: 0.35
                    color: control._grad_clear
                }
                GradientStop {
                    position: 0.85
                    color: control._grad_mid
                }
                GradientStop {
                    position: 1.0
                    color: control._grad_bot
                }
            }
        }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: 4
            color: Theme.accent
            visible: control._red
        }

        Rectangle {
            anchors.fill: parent
            radius: Theme.radius_small
            color: "transparent"
            border.width: 1
            border.color: control._red
                ? Theme.accent
                : (control.activeFocus ? Theme.accent : Theme.button_border)
        }
    }

    Item {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 36

        Text {
            anchors.centerIn: parent
            text: "‹"
            font.pixelSize: 20
            font.bold: true
            color: left_hover.hovered || control._red ? Theme.text_primary : Theme.text_secondary
        }
        HoverHandler {
            id: left_hover
            cursorShape: Qt.PointingHandCursor
        }
        TapHandler {
            id: left_tap
            onTapped: control._step(-1)
        }
    }

    Item {
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 36

        Text {
            anchors.centerIn: parent
            text: "›"
            font.pixelSize: 20
            font.bold: true
            color: right_hover.hovered || control._red ? Theme.text_primary : Theme.text_secondary
        }
        HoverHandler {
            id: right_hover
            cursorShape: Qt.PointingHandCursor
        }
        TapHandler {
            id: right_tap
            onTapped: control._step(1)
        }
    }

    Column {
        anchors.centerIn: parent
        spacing: 5

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: control._index >= 0 ? control.options[control._index].label : ""
            font.pixelSize: Theme.font_small
            font.bold: true
            color: Theme.text_primary
        }

        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 6

            Repeater {
                model: control._count
                delegate: Item {
                    id: bar
                    required property int index
                    width: 16
                    height: 4

                    Rectangle {
                        anchors.fill: parent
                        color: bar.index === control._index
                            ? Theme.text_primary
                            : (bar_hover.hovered ? Theme.text_secondary : Theme.button_border)
                    }
                    HoverHandler {
                        id: bar_hover
                        cursorShape: Qt.PointingHandCursor
                    }
                    TapHandler {
                        onTapped: control._pick(bar.index)
                    }
                }
            }
        }
    }
}
