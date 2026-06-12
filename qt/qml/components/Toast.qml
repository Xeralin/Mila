import QtQuick
import QtQuick.Controls
import ".."

Item {
    id: root
    property bool _error: false

    implicitWidth: label.implicitWidth + 36
    implicitHeight: label.implicitHeight + 22
    opacity: 0
    visible: opacity > 0

    function show(message) {
        _error = false
        _display(message)
    }

    function show_error(message) {
        _error = true
        _display(message)
    }

    function _display(message) {
        label.text = message
        opacity = 1
        timer.restart()
    }

    Rectangle {
        anchors.fill: parent
        radius: Theme.radius_small
        color: Theme.toast_background
        border.color: root._error ? Theme.error : Theme.border
    }

    Label {
        id: label
        anchors.centerIn: parent
        color: Theme.text_primary
    }

    Behavior on opacity { NumberAnimation { duration: 200 } }
    Timer { id: timer; interval: 4000; onTriggered: root.opacity = 0 }
}
